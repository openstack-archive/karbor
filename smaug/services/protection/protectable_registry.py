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

from smaug.services.protection.graph import build_graph

import six


class ProtectableRegistry(object):
    _protectable_map = {}

    @classmethod
    def load_plugins(cls, conf):
        """Load all protectable plugins configured and register them.

        :param conf: The plugin list to load.
        """
        # TODO(yingzhe)
        pass

    @classmethod
    def register_plugin(cls, plugin):
        cls._protectable_map[plugin.get_resource_type()] = plugin

    @classmethod
    def list_resource_types(cls):
        """List all resource types supported by protectables.

        :return: The iterator over supported resource types.
        """
        return six.iterkeys(cls._protectable_map)

    @classmethod
    def list_resources(cls, resource_type):
        """List resource instances of given type.

        :param resource_type: The resource type to list instance.
        :return: The list of resource instance.
        """
        plugin = cls._protectable_map[resource_type]
        return plugin.list_resources()

    @classmethod
    def fetch_dependent_resources(cls, resource):
        """List dependent resources under given parent resource.

        :param resource: The parent resource to list dependent resources.
        :return: The list of dependent resources.
        """
        result = []
        for plugin in six.itervalues(cls._protectable_map):
            if resource.type in plugin.get_parent_resource_types():
                result.extend(plugin.fetch_child_resources(resource))

        return result

    @classmethod
    def build_graph(cls, resources):
        return build_graph(
            start_nodes=resources,
            get_child_nodes_func=cls.fetch_dependent_resources,
        )
