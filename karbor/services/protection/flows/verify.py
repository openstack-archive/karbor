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


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class InitiateVerifyTask(task.Task):
    def execute(self, context, verify, operation_log, *args, **kwargs):
        LOG.debug("Initiate verify verify_id: %s", verify.id)
        verify['status'] = constants.VERIFICATION_STATUS_IN_PROGRESS
        verify.save()
        update_fields = {"status": verify.status}
        utils.update_operation_log(context, operation_log, update_fields)

    def revert(self, context, verify, operation_log, *args, **kwargs):
        LOG.debug("Failed to verify verify_id: %s", verify.id)
        verify['status'] = constants.VERIFICATION_STATUS_FAILURE
        verify.save()
        update_fields = {
            "status": verify.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


class CompleteVerifyTask(task.Task):
    def execute(self, context, verify, operation_log, *args, **kwargs):
        LOG.debug("Complete verify verify_id: %s", verify.id)
        verify['status'] = constants.VERIFICATION_STATUS_SUCCESS
        verify.save()
        update_fields = {
            "status": verify.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


def get_flow(context, workflow_engine, checkpoint, provider, verify):
    resource_graph = checkpoint.resource_graph
    operation_log = utils.create_operation_log_verify(context, verify)
    parameters = verify.parameters
    flow_name = "Verify_" + checkpoint.id
    verify_flow = workflow_engine.build_flow(flow_name, 'linear')
    plugins = provider.load_plugins()
    resources_task_flow = resource_flow.build_resource_flow(
        operation_type=constants.OPERATION_VERIFY,
        context=context,
        workflow_engine=workflow_engine,
        resource_graph=resource_graph,
        plugins=plugins,
        parameters=parameters
    )

    workflow_engine.add_tasks(
        verify_flow,
        InitiateVerifyTask(),
        resources_task_flow,
        CompleteVerifyTask()
    )

    flow_engine = workflow_engine.get_engine(
        verify_flow,
        store={
            'context': context,
            'checkpoint': checkpoint,
            'verify': verify,
            'new_resources': {},
            'operation_log': operation_log
        }
    )
    return flow_engine
