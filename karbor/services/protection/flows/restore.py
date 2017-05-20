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
from oslo_utils import timeutils
from taskflow import task

from karbor.common import constants
from karbor.services.protection.flows import utils
from karbor.services.protection import resource_flow

sync_status_opts = [
    cfg.IntOpt('sync_status_interval',
               default=20,
               help='update protection status interval')
]

CONF = cfg.CONF
CONF.register_opts(sync_status_opts)

LOG = logging.getLogger(__name__)


class InitiateRestoreTask(task.Task):
    def execute(self, context, restore, operation_log, *args, **kwargs):
        LOG.debug("Initiate restore restore_id: %s", restore.id)
        restore['status'] = constants.RESTORE_STATUS_IN_PROGRESS
        restore.save()
        update_fields = {"status": restore.status}
        utils.update_operation_log(context, operation_log, update_fields)

    def revert(self, context, restore, operation_log, *args, **kwargs):
        LOG.debug("Failed to restore restore_id: %s", restore.id)
        restore['status'] = constants.RESTORE_STATUS_FAILURE
        restore.save()
        update_fields = {
            "status": restore.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


class CompleteRestoreTask(task.Task):
    def execute(self, context, restore, operation_log, *args, **kwargs):
        LOG.debug("Complete restore restore_id: %s", restore.id)
        restore['status'] = constants.RESTORE_STATUS_SUCCESS
        restore.save()
        update_fields = {
            "status": restore.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


def get_flow(context, workflow_engine, checkpoint, provider, restore,
             restore_auth):
    resource_graph = checkpoint.resource_graph
    operation_log = utils.create_operation_log_restore(context, restore)
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
        resources_task_flow,
        CompleteRestoreTask()
    )
    flow_engine = workflow_engine.get_engine(
        restore_flow,
        store={
            'context': context,
            'checkpoint': checkpoint,
            'restore': restore,
            'new_resources': {},
            'operation_log': operation_log
        }
    )
    return flow_engine
