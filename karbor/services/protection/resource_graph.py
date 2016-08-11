#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from karbor.common import constants
from karbor.i18n import _, _LE
from karbor.services.protection.graph import GraphWalkerListener
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


class ResourceGraphContext(object):
    def __init__(self, cntxt, is_first_visited=False, operation="protect",
                 parameters=None, plugin_map=None, node=None,
                 workflow_engine=None, task_flow=None, checkpoint=None,
                 heat_template=None):
        self.cntxt = cntxt
        self.is_first_visited = is_first_visited
        self.operation = operation
        self.parameters = parameters
        self.plugin_map = plugin_map
        self.node = node
        self.workflow_engine = workflow_engine
        self.task_flow = task_flow
        self.task_stack = []

        # used for protection
        self.status_getters = []

        # used for restoration
        self.checkpoint = checkpoint
        self.heat_template = heat_template

    def get_node_context(self, node, is_first_visited=None):
        node_context = ResourceGraphContext(
            self.cntxt,
            is_first_visited=is_first_visited,
            operation=self.operation,
            parameters=self.parameters,
            plugin_map=self.plugin_map,
            node=node,
            workflow_engine=self.workflow_engine,
            task_flow=self.task_flow,
            checkpoint=self.checkpoint,
            heat_template=self.heat_template
        )
        node_context.task_stack = self.task_stack
        node_context.status_getters = self.status_getters
        return node_context


class ResourceGraphWalkerListener(GraphWalkerListener):
    def __init__(self, context):
        self.context = context
        self.plugin_map = self.context.plugin_map

    def on_node_enter(self, node, already_visited):
        resource = node.value
        resource_type = resource.type
        LOG.info(_("on_node_enter, node resource_type:%s"), resource_type)
        protection_plugin = self._get_protection_plugin(resource_type)

        # get node context
        is_first_visited = not already_visited
        context = self.context.get_node_context(node, is_first_visited)
        # do something in protection_plugin
        protection_plugin.on_resource_start(context)

        if self.context.operation == constants.OPERATION_PROTECT \
                or self.context.operation == constants.OPERATION_DELETE:
            if not already_visited:
                self.context.status_getters.append(
                    {"resource_id": resource.id,
                     "get_resource_stats": protection_plugin.get_resource_stats
                     }
                )

    def on_node_exit(self, node):
        resource = node.value
        resource_type = resource.type
        LOG.info(_("on_node_exit, node resource_type:%s"), resource_type)
        protection_plugin = self._get_protection_plugin(resource_type)

        # get node context
        context = self.context.get_node_context(node)
        # do something in protection_plugin
        protection_plugin.on_resource_end(context)

    def _get_protection_plugin(self, resource_type):
        for plugin in self.plugin_map.values():
            if hasattr(plugin, "get_supported_resources_types"):
                if resource_type in plugin.get_supported_resources_types():
                    return plugin
        LOG.error(_LE("no plugin support this resource_type:%s"),
                  resource_type)
        raise Exception(_("No plugin support this resource_type"))
