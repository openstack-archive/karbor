# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
from karbor import resource
from karbor.services.protection import protectable_plugin


class ProjectProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """Keystone project protectable plugin"""
    _SUPPORT_RESOURCE_TYPE = constants.PROJECT_RESOURCE_TYPE

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return ()

    def list_resources(self, context, parameters=None):
        # TODO(yuvalbr) handle admin context for multiple projects?
        return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                  id=context.project_id,
                                  name=context.project_name)]

    def get_dependent_resources(self, context, parent_resource):
        pass

    def show_resource(self, context, resource_id, parameters=None):
        # TODO(yinwei) get project name through keystone client
        return resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                 id=resource_id,
                                 name=context.project_name)
