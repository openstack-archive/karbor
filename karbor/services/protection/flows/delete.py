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

from karbor.common import constants
from karbor.services.protection.flows import utils
from karbor.services.protection import resource_flow
from oslo_log import log as logging
from oslo_utils import timeutils

from taskflow import task

LOG = logging.getLogger(__name__)


class InitiateDeleteTask(task.Task):
    def execute(self, context, checkpoint, operation_log, *args, **kwargs):
        LOG.debug("Initiate delete checkpoint_id: %s", checkpoint.id)
        checkpoint.status = constants.CHECKPOINT_STATUS_DELETING
        checkpoint.commit()
        update_fields = {"status": checkpoint.status}
        utils.update_operation_log(context, operation_log, update_fields)

    def revert(self, context, checkpoint, operation_log, *args, **kwargs):
        LOG.debug("Failed to delete checkpoint_id: %s", checkpoint.id)
        checkpoint.status = constants.CHECKPOINT_STATUS_ERROR_DELETING
        checkpoint.commit()
        update_fields = {
            "status": checkpoint.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


class CompleteDeleteTask(task.Task):
    def execute(self, context, checkpoint, operation_log):
        LOG.debug("Complete delete checkpoint_id: %s", checkpoint.id)
        checkpoint.delete()
        update_fields = {
            "status": checkpoint.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


def get_flow(context, workflow_engine, checkpoint, provider):
    LOG.info("Start get checkpoint flow, checkpoint_id: %s", checkpoint.id)
    flow_name = "Delete_Checkpoint_" + checkpoint.id
    delete_flow = workflow_engine.build_flow(flow_name, 'linear')
    resource_graph = checkpoint.resource_graph
    operation_log = utils.create_operation_log(context, checkpoint)
    plugins = provider.load_plugins()
    resources_task_flow = resource_flow.build_resource_flow(
        operation_type=constants.OPERATION_DELETE,
        context=context,
        workflow_engine=workflow_engine,
        resource_graph=resource_graph,
        plugins=plugins,
        parameters=None
    )
    workflow_engine.add_tasks(
        delete_flow,
        InitiateDeleteTask(),
        resources_task_flow,
        CompleteDeleteTask(),
    )
    flow_engine = workflow_engine.get_engine(
        delete_flow,
        store={
            'context': context,
            'checkpoint': checkpoint,
            'operation_log': operation_log}
    )
    return flow_engine
