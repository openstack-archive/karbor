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
from karbor.resource import Resource
from karbor.services.protection import resource_flow
from oslo_log import log as logging
from taskflow import task

LOG = logging.getLogger(__name__)


class InitiateProtectTask(task.Task):
    def execute(self, checkpoint, *args, **kwargs):
        LOG.debug("Initiate protect checkpoint_id: %s", checkpoint.id)
        checkpoint.status = constants.CHECKPOINT_STATUS_PROTECTING
        checkpoint.commit()

    def revert(self, checkpoint, *args, **kwargs):
        LOG.debug("Failed to protect checkpoint_id: %s", checkpoint.id)
        checkpoint.status = constants.CHECKPOINT_STATUS_ERROR
        checkpoint.commit()


class CompleteProtectTask(task.Task):
    def execute(self, checkpoint):
        LOG.debug("Complete protect checkpoint_id: %s", checkpoint.id)
        checkpoint.status = constants.CHECKPOINT_STATUS_AVAILABLE
        checkpoint.commit()


def get_flow(context, protectable_registry, workflow_engine, plan, provider,
             checkpoint):
    resources = set(Resource(**item) for item in plan.get("resources"))
    resource_graph = protectable_registry.build_graph(context,
                                                      resources)
    checkpoint.resource_graph = resource_graph
    checkpoint.commit()
    flow_name = "Protect_" + plan.get('id')
    protection_flow = workflow_engine.build_flow(flow_name, 'linear')
    plugins = provider.load_plugins()
    resources_task_flow = resource_flow.build_resource_flow(
        operation_type=constants.OPERATION_PROTECT,
        context=context,
        workflow_engine=workflow_engine,
        resource_graph=resource_graph,
        plugins=plugins,
        parameters=plan.get('parameters'),
    )
    workflow_engine.add_tasks(
        protection_flow,
        InitiateProtectTask(),
        resources_task_flow,
        CompleteProtectTask(),
    )
    flow_engine = workflow_engine.get_engine(protection_flow, store={
        'checkpoint': checkpoint
    })
    return flow_engine
