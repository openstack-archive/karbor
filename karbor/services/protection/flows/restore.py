# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import uuidutils

from karbor.common import constants
from karbor.services.protection import client_factory
from karbor.services.protection import resource_flow
from karbor.services.protection import restore_heat
from taskflow import task

sync_status_opts = [
    cfg.IntOpt('sync_status_interval',
               default=20,
               help='update protection status interval')
]

CONF = cfg.CONF
CONF.register_opts(sync_status_opts)

LOG = logging.getLogger(__name__)


class InitiateRestoreTask(task.Task):
    def execute(self, restore, *args, **kwargs):
        LOG.debug("Initiate restore restore_id: %s", restore.id)
        restore['status'] = constants.RESTORE_STATUS_IN_PROGRESS
        restore.save()

    def revert(self, restore, *args, **kwargs):
        LOG.debug("Failed to restore restore_id: %s", restore.id)
        restore['status'] = constants.RESTORE_STATUS_FAILURE
        restore.save()


class CompleteRestoreTask(task.Task):
    def execute(self, restore, *args, **kwargs):
        LOG.debug("Complete restore restore_id: %s", restore.id)
        restore['status'] = constants.RESTORE_STATUS_SUCCESS
        restore.save()


class CreateHeatTask(task.Task):
    default_provides = ['heat_client', 'heat_template']

    def execute(self, context, heat_conf):
        LOG.info('Creating Heat template. Target: "%s"'
                 % heat_conf.get('auth_url', '(None)'))
        heat_client = client_factory.ClientFactory.create_client(
            'heat', context=context, **heat_conf)

        heat_template = restore_heat.HeatTemplate()

        return (heat_client, heat_template)


class CreateStackTask(task.Task):
    default_provides = 'stack_id'

    def execute(self, heat_client, heat_template):
        stack_name = "restore_%s" % uuidutils.generate_uuid()
        if heat_template.len() == 0:
            LOG.info('Not creating Heat stack, no resources in template')
            return None
        LOG.info('Creating Heat stack, stack_name: %s', stack_name)
        try:
            body = heat_client.stacks.create(
                stack_name=stack_name,
                template=heat_template.to_dict())
            LOG.debug('Created stack with id: %s', body['stack']['id'])
            return body['stack']['id']
        except Exception:
            LOG.error("use heat to create stack failed")
            raise


class SyncRestoreStatusTask(task.Task):
    def execute(self, stack_id, heat_client, restore):
        if stack_id is None:
            LOG.info('Not syncing Heat stack status, stack is empty')
            return

        LOG.info('Syncing Heat stack status, stack_id: %s', stack_id)
        self._restore = restore
        sync_status_loop = loopingcall.FixedIntervalLoopingCall(
            self._sync_status, heat_client, stack_id)
        sync_status_loop.start(interval=CONF.sync_status_interval)
        sync_status_loop.wait()

    def _sync_status(self, heat_client, stack_id):
        try:
            stack = heat_client.stacks.get(stack_id)
        except Exception:
            LOG.debug('Heat error getting stack, stack_id: %s', stack_id)
            raise
        stack_status = getattr(stack, 'stack_status')
        if stack_status == 'CREATE_IN_PROGRESS':
            LOG.debug('Heat stack status: in progress, stack_id: %s',
                      stack_id)
        elif stack_status == 'CREATE_COMPLETE':
            LOG.info('Heat stack status: complete, stack_id: %s', stack_id)
            self._update_resource_status(heat_client, stack_id)
            raise loopingcall.LoopingCallDone()
        else:
            LOG.info('Heat stack status: failure, stack_id: %s', stack_id)
            self._update_resource_status(heat_client, stack_id)
            raise

    def _update_resource_status(self, heat_client, stack_id):
        LOG.debug('Updating resources status from heat stack (stack_id: %s)',
                  stack_id)
        try:
            resources = heat_client.resources.list(stack_id)
            for resource in resources:
                heat_to_karbor_map = {
                    'CREATE_COMPLETE': constants.RESOURCE_STATUS_AVAILABLE,
                    'CREATE_IN_PROGRESS': constants.RESOURCE_STATUS_RESTORING,
                    'CREATE_FAILED': constants.RESOURCE_STATUS_ERROR,
                }
                reason = resource.resource_status_reason if (
                    resource.resource_status == 'CREATE_FAILED'
                ) else None
                self._restore.update_resource_status(
                    resource.resource_type,
                    resource.physical_resource_id,
                    heat_to_karbor_map[resource.resource_status],
                    reason,
                )
            self._restore.save()
        except Exception as e:
            LOG.warning('Unable to update resources status from heat stack. '
                        'Reason: %s', e)


def get_flow(context, workflow_engine, checkpoint, provider, restore,
             restore_auth):
    target = restore.get('restore_target', None)

    heat_conf = {}
    if target is not None:
        heat_conf["auth_url"] = target
        if restore_auth is not None:
            auth_type = restore_auth.get("type", None)
            if auth_type == "password":
                heat_conf["username"] = restore_auth["username"]
                heat_conf["password"] = restore_auth["password"]

    resource_graph = checkpoint.resource_graph
    parameters = restore.parameters
    flow_name = "Restore_" + checkpoint.id
    restore_flow = workflow_engine.build_flow(flow_name, 'linear')
    plugins = provider.load_plugins()
    resources_task_flow = resource_flow.build_resource_flow(
        operation_type=constants.OPERATION_RESTORE,
        context=context,
        workflow_engine=workflow_engine,
        resource_graph=resource_graph,
        plugins=plugins,
        parameters=parameters
    )

    workflow_engine.add_tasks(
        restore_flow,
        InitiateRestoreTask(),
        CreateHeatTask(inject={'context': context, 'heat_conf': heat_conf}),
        resources_task_flow,
        CreateStackTask(),
        SyncRestoreStatusTask(),
        CompleteRestoreTask()
    )
    flow_engine = workflow_engine.get_engine(restore_flow,
                                             store={'checkpoint': checkpoint,
                                                    'restore': restore})
    return flow_engine
