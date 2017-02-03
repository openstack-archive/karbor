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
from karbor.services.protection import protection_plugin


class NeutronProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.NETWORK_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(NeutronProtectionPlugin, self).__init__(config)

    @classmethod
    def get_supported_resources_types(self):
        return self._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(self, resources_type):
        # TODO(chenhuayi)
        pass

    @classmethod
    def get_restore_schema(self, resources_type):
        # TODO(chenhuayi)
        pass

    @classmethod
    def get_saved_info_schema(self, resources_type):
        # TODO(chenhuayi)
        pass

    @classmethod
    def get_saved_info(self, metadata_store, resource):
        # TODO(chenhuayi)
        pass

    def get_protect_operation(self, resource):
        # TODO(chenhuayi)
        pass

    def get_restore_operation(self, resource):
        # TODO(chenhuayi)
        pass

    def get_delete_operation(self, resource):
        # TODO(chenhuayi)
        pass
