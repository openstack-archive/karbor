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

import six

from oslo_log import log as logging
from smaug import exception
from smaug.i18n import _
from smaug.services.protection.graph import build_graph
from stevedore import extension

LOG = logging.getLogger(__name__)


class ProtectablePluginLoadFailed(exception.SmaugException):
    message = _("Could not load %(name)s: %(error)s")


def _raise_extension_exception(extmanager, ep, err):
    raise ProtectablePluginLoadFailed(name=ep.name,
                                      error=six.text_type(err))


class ProtectableRegistry(object):
    _plugin_map = {}

    def __init__(self, cntx):
        self._context = cntx
        self._protectable_map = {}

    @classmethod
    def load_plugins(cls):
        """Load all protectable plugins configured and register them.

        """
        mgr = extension.ExtensionManager(
            namespace='smaug.protectables',
            invoke_on_load=True,
            on_load_failure_callback=_raise_extension_exception)

        for e in mgr:
            cls.register_plugin(e.obj)

    @classmethod
    def register_plugin(cls, plugin):
        cls._plugin_map[plugin.get_resource_type()] = plugin

    @classmethod
    def create_instance(cls, cntx):
        return cls(cntx)

    def _get_protectable(self, resource_type):
        if resource_type in self._protectable_map:
            return self._protectable_map[resource_type]

        protectable = self._plugin_map[resource_type].instance(self._context)
        self._protectable_map[resource_type] = protectable
        return protectable

    @classmethod
    def list_resource_types(cls):
        """List all resource types supported by protectables.

        :return: The list of supported resource types.
        """
        return [type for type in six.iterkeys(cls._plugin_map)]

    @classmethod
    def get_protectable_resource_plugin(cls, resource_type):
        """Get the protectable plugin with the specified type."""
        return cls._plugin_map.get(resource_type)

    def list_resources(self, resource_type):
        """List resource instances of given type.

        :param resource_type: The resource type to list instance.
        :return: The list of resource instance.
        """
        protectable = self._get_protectable(resource_type)
        return protectable.list_resources()

    def fetch_dependent_resources(self, resource):
        """List dependent resources under given parent resource.

        :param resource: The parent resource to list dependent resources.
        :return: The list of dependent resources.
        """
        result = []
        for plugin in six.itervalues(self._plugin_map):
            if resource.type in plugin.get_parent_resource_types():
                protectable = self._get_protectable(
                    plugin.get_resource_type())
                result.extend(protectable.get_dependent_resources(resource))

        return result

    def build_graph(self, resources):
        return build_graph(
            start_nodes=resources,
            get_child_nodes_func=self.fetch_dependent_resources,
        )
