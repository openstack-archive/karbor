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

    def __init__(self, context=None):
        super(ProtectablePlugin, self).__init__()
        self._context = context

    def instance(self, context):
        return self.__class__(context)

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
    def list_resources(self, context, parameters=None):
        """List resource instances of type this plugin supported.

        :return: The list of resource instance.
        """
        pass

    @abc.abstractmethod
    def show_resource(self, context, resource_id, parameters=None):
        """Show resource detail information.

        """
        pass

    @abc.abstractmethod
    def get_dependent_resources(self, context, parent_resource):
        """List dependent resource instances.

        The listed resource instances are of type this plugin supported,
        and dependent by the given parent resource.

        :param parent_resource: the parent resource instance.
        :type parent_resource: one of parent resource types.
        :return: the list of dependent resource instances.
        """
        pass
