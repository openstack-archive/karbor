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

from karbor import exception
from karbor.i18n import _
from karbor.services.protection.graph import build_graph
import six

from stevedore import extension


class ProtectablePluginLoadFailed(exception.KarborException):
    message = _("Could not load %(name)s: %(error)s")


def _raise_extension_exception(extmanager, ep, err):
    raise ProtectablePluginLoadFailed(name=ep.name,
                                      error=six.text_type(err))


class ProtectableRegistry(object):

    def __init__(self):
        super(ProtectableRegistry, self).__init__()
        self._protectable_map = {}
        self._plugin_map = {}

    def load_plugins(self):
        """Load all protectable plugins configured and register them.

        """
        mgr = extension.ExtensionManager(
            namespace='karbor.protectables',
            invoke_on_load=True,
            on_load_failure_callback=_raise_extension_exception)

        for e in mgr:
            self.register_plugin(e.obj)

    def register_plugin(self, plugin):
        self._plugin_map[plugin.get_resource_type()] = plugin

    def _get_protectable(self, context, resource_type):
        if resource_type in self._protectable_map:
            return self._protectable_map[resource_type]

        protectable = self._plugin_map[resource_type].instance(context)
        self._protectable_map[resource_type] = protectable
        return protectable

    def list_resource_types(self):
        """List all resource types supported by protectables.

        :return: The list of supported resource types.
        """
        return [type for type in six.iterkeys(self._plugin_map)]

    def get_protectable_resource_plugin(self, resource_type):
        """Get the protectable plugin with the specified type."""
        return self._plugin_map.get(resource_type)

    def list_resources(self, context, resource_type, parameters=None):
        """List resource instances of given type.

        :param resource_type: The resource type to list instance.
        :return: The list of resource instance.
        """
        protectable = self._get_protectable(context, resource_type)
        return protectable.list_resources(context, parameters=parameters)

    def show_resource(self, context, resource_type, resource_id,
                      parameters=None):
        """List resource instances of given type.

        :param resource_type: The resource type of instance.
        :param resource_id: The resource id of instance.
        :return: The show of resource instance.
        """
        protectable = self._get_protectable(context, resource_type)
        return protectable.show_resource(context, resource_id,
                                         parameters=parameters)

    def fetch_dependent_resources(self, context, resource):
        """List dependent resources under given parent resource.

        :param resource: The parent resource to list dependent resources.
        :return: The list of dependent resources.
        """
        result = []
        for plugin in six.itervalues(self._plugin_map):
            if resource.type in plugin.get_parent_resource_types():
                protectable = self._get_protectable(
                    context,
                    plugin.get_resource_type())
                result.extend(protectable.get_dependent_resources(context,
                                                                  resource))

        return result

    def build_graph(self, context, resources):
        def fetch_dependent_resources_context(resource):
            return self.fetch_dependent_resources(context, resource)

        return build_graph(
            start_nodes=resources,
            get_child_nodes_func=fetch_dependent_resources_context,
        )
