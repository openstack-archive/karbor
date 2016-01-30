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

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class ProtectablePlugin(object):
    """Base abstract class for protectable plugin.

    """

    @abc.abstractmethod
    def get_resource_type(self):
        """Return the resource type that this plugin supports.

        Subclasses can implement as a classmethod
        """
        pass

    @abc.abstractmethod
    def get_parent_resource_types(self):
        """Return the possible parent resource types.

        Subclasses can implement as a classmethod
        """
        pass

    @abc.abstractmethod
    def list_resources(self):
        """List resource instances of resource_type.

        :return: The list of resource instance.
        """
        pass

    @abc.abstractmethod
    def fetch_child_resources(self, parent_resource):
        """List child resources of resource_type under given parent resource.

        :param parent_resource: The parent resource to list child resources.
        :return: The list of child resources of resource_type.
        """
        pass
