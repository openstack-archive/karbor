# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
from collections import namedtuple

from karbor.common import constants
from karbor import exception
from karbor.services.protection import graph
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


HOOKS = (
    HOOK_PRE_BEGIN,
    HOOK_PRE_FINISH,
    HOOK_MAIN,
    HOOK_COMPLETE
) = (
    'on_prepare_begin',
    'on_prepare_finish',
    'on_main',
    'on_complete'
)

ResourceHooks = namedtuple('ResourceHooks', [
    HOOK_PRE_BEGIN,
    HOOK_PRE_FINISH,
    HOOK_MAIN,
    HOOK_COMPLETE,
])


OPERATION_EXTRA_ARGS = {
    constants.OPERATION_RESTORE: ['heat_template', 'restore'],
}


def noop_handle(*args, **kwargs):
    pass


class ResourceFlowGraphWalkerListener(graph.GraphWalkerListener):
    def __init__(self, resource_flow, operation_type, context, parameters,
                 plugins, workflow_engine):
        super(ResourceFlowGraphWalkerListener, self).__init__()
        self.operation_type = operation_type
        self.context = context
        self.parameters = parameters or {}
        self.plugins = plugins
        self.workflow_engine = workflow_engine
        self.flow = resource_flow

        self.node_tasks = {}
        self.task_stack = []
        self.current_resource = None

    def _create_hook_tasks(self, operation_obj, resource):
        pre_begin_task = self._create_hook_task(operation_obj, resource,
                                                HOOK_PRE_BEGIN)
        pre_finish_task = self._create_hook_task(operation_obj, resource,
                                                 HOOK_PRE_FINISH)
        main_task = self._create_hook_task(operation_obj, resource,
                                           HOOK_MAIN)
        post_task = self._create_hook_task(operation_obj, resource,
                                           HOOK_COMPLETE)

        return ResourceHooks(pre_begin_task, pre_finish_task, main_task,
                             post_task)

    def _create_hook_task(self, operation_obj, resource, hook_type):
        method = getattr(operation_obj, hook_type, noop_handle)
        assert callable(method), (
            'Resource {} method "{}" is not callable'
        ).format(resource.type, hook_type)

        task_name = "{operation_type}_{hook_type}_{type}_{id}".format(
            type=resource.type,
            id=resource.id,
            hook_type=hook_type,
            operation_type=self.operation_type,
        )

        parameters = {}
        parameters.update(self.parameters.get(resource.type, {}))
        resource_id = '{}#{}'.format(resource.type, resource.id)
        parameters.update(self.parameters.get(resource_id, {}))
        injects = {
            'context': self.context,
            'parameters': parameters,
            'resource': resource,
        }
        requires = list(injects)
        requires.append('checkpoint')
        requires.extend(OPERATION_EXTRA_ARGS.get(self.operation_type, []))

        task = self.workflow_engine.create_task(method,
                                                name=task_name,
                                                inject=injects,
                                                requires=requires)
        return task

    def on_node_enter(self, node, already_visited):
        resource = node.value
        LOG.debug(
            "Enter node (type: %(type)s id: %(id)s visited: %(visited)s)",
            {"type": resource.type, "id": resource.id, "visited":
             already_visited}
        )
        self.current_resource = resource
        if already_visited:
            self.task_stack.append(self.node_tasks[resource.id])
            return

        if resource.type not in self.plugins:
            raise exception.ProtectionPluginNotFound(type=resource.type)

        protection_plugin = self.plugins[resource.type]
        operation_getter_name = 'get_{}_operation'.format(self.operation_type)
        operation_getter = getattr(protection_plugin, operation_getter_name)
        assert callable(operation_getter)
        operation_obj = operation_getter(resource)
        hooks = self._create_hook_tasks(operation_obj, resource)
        LOG.debug("added operation %s hooks", self.operation_type)
        self.node_tasks[resource.id] = hooks
        self.task_stack.append(hooks)
        self.workflow_engine.add_tasks(self.flow, hooks.on_prepare_begin,
                                       hooks.on_prepare_finish, hooks.on_main,
                                       hooks.on_complete)
        self.workflow_engine.link_task(self.flow, hooks.on_prepare_begin,
                                       hooks.on_prepare_finish)
        self.workflow_engine.link_task(self.flow, hooks.on_prepare_finish,
                                       hooks.on_main)
        self.workflow_engine.link_task(self.flow, hooks.on_main,
                                       hooks.on_complete)

    def on_node_exit(self, node):
        resource = node.value
        LOG.debug(
            "Exit node (type: %(type)s id: %(id)s)",
            {"type": resource.type, "id": resource.id}
        )
        child_hooks = self.task_stack.pop()
        if len(self.task_stack) > 0:
            parent_hooks = self.task_stack[-1]
            self.workflow_engine.link_task(self.flow,
                                           parent_hooks.on_prepare_begin,
                                           child_hooks.on_prepare_begin)
            self.workflow_engine.link_task(self.flow,
                                           child_hooks.on_prepare_finish,
                                           parent_hooks.on_prepare_finish)
            self.workflow_engine.link_task(self.flow, child_hooks.on_complete,
                                           parent_hooks.on_complete)


def build_resource_flow(operation_type, context, workflow_engine,
                        plugins, resource_graph, parameters):
    LOG.info("Build resource flow for operation %s", operation_type)

    resource_graph_flow = workflow_engine.build_flow(
        'ResourceGraphFlow_{}'.format(operation_type),
        'graph',
    )
    resource_walker = ResourceFlowGraphWalkerListener(resource_graph_flow,
                                                      operation_type,
                                                      context,
                                                      parameters,
                                                      plugins,
                                                      workflow_engine)
    walker = graph.GraphWalker()
    walker.register_listener(resource_walker)
    LOG.debug("Starting resource graph walk (operation %s)", operation_type)
    walker.walk_graph(resource_graph)
    LOG.debug("Finished resource graph walk (operation %s)", operation_type)
    return resource_graph_flow
