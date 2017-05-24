# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


class Operation(object):
    def on_prepare_begin(self, checkpoint, resource, context, parameters,
                         **kwargs):
        """on_prepare_begin hook runs before any child resource's hooks run

        Optional
        :param checkpoint: checkpoint object for this operation
        :param resource: a resource object for this operation
        :param context: current operation context (viable for clients)
        :param parameters: dictionary representing operation parameters
        :param restore: Restore object for restore operation only
        :param heat_template: HeatTemplate for restore operation only
        """
        pass

    def on_prepare_finish(self, checkpoint, resource, context, parameters,
                          **kwargs):
        """on_prepare_finish hook runs after all child resources' prepare hooks

        Optional
        :param checkpoint: checkpoint object for this operation
        :param resource: a resource object for this operation
        :param context: current operation context (viable for clients)
        :param parameters: dictionary representing operation parameters
        :param restore: Restore object for restore operation only
        :param heat_template: HeatTemplate for restore operation only
        """
        pass

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        """on_main hook runs in parallel to other resources' on_main hooks

        Your main operation heavy lifting should probably be here.
        Optional
        :param checkpoint: checkpoint object for this operation
        :param resource: a resource object for this operation
        :param context: current operation context (viable for clients)
        :param parameters: dictionary representing operation parameters
        :param restore: Restore object for restore operation only
        :param heat_template: HeatTemplate for restore operation only
        """
        pass

    def on_complete(self, checkpoint, resource, context, parameters, **kwargs):
        """on_complete hook runs after all dependent resource's hooks

        Optional
        :param checkpoint: checkpoint object for this operation
        :param resource: a resource object for this operation
        :param context: current operation context (viable for clients)
        :param parameters: dictionary representing operation parameters
        :param restore: Restore object for restore operation only
        :param heat_template: HeatTemplate for restore operation only
        """
        pass


class ProtectionPlugin(object):
    def __init__(self, config=None):
        super(ProtectionPlugin, self).__init__()
        self._config = config

    def get_protect_operation(self, resource):
        """Returns the protect Operation for this resource

        :returns: Operation for the resource
        """
        raise NotImplementedError

    def get_restore_operation(self, resource):
        """Returns the restore Operation for this resource

        :returns: Operation for the resource
        """
        raise NotImplementedError

    def get_delete_operation(self, resource):
        """Returns the delete Operation for this resource

        :returns: Operation for the resource
        """
        raise NotImplementedError

    @classmethod
    def get_supported_resources_types(cls):
        """Returns a list of resource types this plugin supports

        :returns: a list of resource types
        """
        raise NotImplementedError

    @classmethod
    def get_options_schema(cls, resource_type):
        """Returns the protect options schema for a resource type

        :returns: a dictionary representing the schema
        """
        raise NotImplementedError

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        """Returns the saved info schema for a resource type

        :returns: a dictionary representing the schema
        """
        raise NotImplementedError

    @classmethod
    def get_restore_schema(cls, resource_type):
        """Returns the restore schema for a resource type

        :returns: a dictionary representing the schema
        """
        raise NotImplementedError

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        """Returns the saved info for a resource

        :returns: a dictionary representing the saved info
        """
        raise NotImplementedError
