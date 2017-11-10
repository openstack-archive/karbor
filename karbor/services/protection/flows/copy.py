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
from karbor import exception
from karbor.resource import Resource
from karbor.services.protection.flows import utils
from karbor.services.protection import resource_flow
from oslo_log import log as logging
from oslo_utils import timeutils

from oslo_serialization import jsonutils

from taskflow import task

LOG = logging.getLogger(__name__)


class InitiateCopyTask(task.Task):
    def execute(self, context, checkpoint, checkpoint_copy, operation_log,
                *args, **kwargs):
        LOG.debug("Initiate copy checkpoint_id: %s", checkpoint_copy.id)
        checkpoint_copy.status = constants.CHECKPOINT_STATUS_COPYING
        checkpoint_copy.commit()
        update_fields = {"status": checkpoint_copy.status}
        utils.update_operation_log(context, operation_log, update_fields)

    def revert(self, context, checkpoint, checkpoint_copy, operation_log,
               *args, **kwargs):
        LOG.debug("Failed to copy checkpoint_id: %s", checkpoint_copy.id)
        checkpoint_copy.status = constants.CHECKPOINT_STATUS_ERROR
        checkpoint_copy.commit()
        update_fields = {
            "status": checkpoint_copy.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


class CompleteCopyTask(task.Task):
    def execute(self, context, checkpoint, checkpoint_copy, operation_log):
        LOG.debug("Complete copy checkpoint_id: %s", checkpoint_copy.id)
        checkpoint_copy.status = constants.CHECKPOINT_STATUS_AVAILABLE
        if checkpoint_copy.extra_info:
            extra_info = jsonutils.loads(checkpoint_copy.extra_info)
            extra_info['copy_status'] = \
                constants.CHECKPOINT_STATUS_COPY_FINISHED
        else:
            extra_info = {
                'copy_status': constants.CHECKPOINT_STATUS_COPY_FINISHED}
        checkpoint_copy.extra_info = jsonutils.dumps(extra_info)
        checkpoint_copy.commit()
        update_fields = {
            "status": checkpoint_copy.status,
            "ended_at": timeutils.utcnow()
        }
        utils.update_operation_log(context, operation_log, update_fields)


def get_flow(context, protectable_registry, workflow_engine, plan, provider,
             checkpoint, checkpoint_copy):
    resources = set(Resource(**item) for item in plan.get("resources"))
    resource_graph = protectable_registry.build_graph(context,
                                                      resources)
    checkpoint_copy.resource_graph = resource_graph
    checkpoint_copy.commit()
    operation_log = utils.create_operation_log(context, checkpoint_copy,
                                               constants.OPERATION_COPY)
    flow_name = "Copy_" + plan.get('id')+checkpoint.id
    copy_flow = workflow_engine.build_flow(flow_name, 'linear')
    plugins = provider.load_plugins()
    parameters = {}
    parameters.update(plan.get('parameters', {}))
    parameters['checkpoint'] = checkpoint
    parameters['checkpoint_copy'] = checkpoint_copy
    parameters['operation_log'] = operation_log
    resources_task_flow = resource_flow.build_resource_flow(
        operation_type=constants.OPERATION_COPY,
        context=context,
        workflow_engine=workflow_engine,
        resource_graph=resource_graph,
        plugins=plugins,
        parameters=parameters,
    )
    store_dict = {'context': context,
                  'checkpoint': checkpoint,
                  'checkpoint_copy': checkpoint_copy,
                  'operation_log': operation_log
                  }
    workflow_engine.add_tasks(
        copy_flow,
        InitiateCopyTask(name='InitiateCopyTask_'+checkpoint_copy.id,
                         inject=store_dict),
        resources_task_flow,
        CompleteCopyTask(name='CompleteCopyTask_'+checkpoint_copy.id,
                         inject=store_dict),
    )
    return copy_flow


def get_flows(context, protectable_registry, workflow_engine, plan, provider,
              checkpoints, checkpoint_collection):
    checkpoints_protect_copy = prepare_create_flows(
        context, plan, checkpoints, checkpoint_collection)

    copy_flows = create_flows(
        context, protectable_registry, workflow_engine, plan, provider,
        checkpoints_protect_copy, checkpoint_collection)

    return copy_flows, checkpoints_protect_copy


def prepare_create_flows(context, plan, checkpoints, checkpoint_collection):
    LOG.debug("Creating checkpoint copy for plan. plan: %s", plan.id)
    checkpoints_protect_copy = []
    for checkpoint in checkpoints:
        extra_info = checkpoint.get("extra_info", None)
        copy_status = None
        if extra_info:
            extra_info = jsonutils.loads(extra_info)
            copy_status = extra_info.get('copy_status', None)
        if (checkpoint.get("status") !=
                constants.CHECKPOINT_STATUS_AVAILABLE) or (
                    copy_status ==
                    constants.CHECKPOINT_STATUS_COPY_FINISHED):
            continue
        checkpoint_dict = {
            'project_id': context.project_id,
            'status': constants.CHECKPOINT_STATUS_WAIT_COPYING,
            'provider_id': checkpoint.get("provider_id"),
            "protection_plan": checkpoint.get("protection_plan"),
            "extra_info": {}
        }
        checkpoint_copy = checkpoint_collection.create(plan,
                                                       checkpoint_dict)
        checkpoint_protect_copy = {
            'checkpoint_protect_id': checkpoint.get("id"),
            'checkpoint_copy_id': checkpoint_copy.id
        }
        checkpoints_protect_copy.append(checkpoint_protect_copy)
    LOG.debug("The protect and copy checkpoints . checkpoints_copy: %s",
              checkpoints_protect_copy)
    return checkpoints_protect_copy


def create_flows(context, protectable_registry, workflow_engine,
                 plan, provider, checkpoints_protect_copy,
                 checkpoint_collection):
    LOG.debug("Creating flows for the plan. checkpoints: %s",
              checkpoints_protect_copy)
    flow_name = "Copy_flows" + plan.get('id')
    copy_flows = workflow_engine.build_flow(flow_name, 'linear')
    for checkpoint_protect_copy in checkpoints_protect_copy:
        checkpoint_protect_id = checkpoint_protect_copy.get(
            "checkpoint_protect_id")
        checkpoint_copy_id = checkpoint_protect_copy.get(
            "checkpoint_copy_id")
        checkpoint_protect = checkpoint_collection.get(checkpoint_protect_id)
        checkpoint_copy = checkpoint_collection.get(checkpoint_copy_id)
        try:
            copy_flow = get_flow(
                context,
                protectable_registry,
                workflow_engine,
                plan,
                provider,
                checkpoint_protect,
                checkpoint_copy,
            )
        except Exception as e:
            LOG.exception("Failed to create copy flow, checkpoint: %s",
                          checkpoint_protect_id)
            raise exception.FlowError(
                flow="copy",
                error=e.msg if hasattr(e, 'msg') else 'Internal error')
        workflow_engine.add_tasks(copy_flows, copy_flow)
    flows_engine = workflow_engine.get_engine(copy_flows, store={
        'context': context
    })
    LOG.debug("Creating flows for the plan. copy_flows: %s", copy_flows)

    return flows_engine
