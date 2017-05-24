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

from karbor.common import constants
from karbor.services.protection import protection_plugin


class NoopOperation(protection_plugin.Operation):
    def on_prepare_begin(self, *args, **kwargs):
        pass

    def on_prepare_finish(self, *args, **kwargs):
        pass

    def on_main(self, *args, **kwargs):
        pass

    def on_complete(self, *args, **kwargs):
        pass


class NoopProtectionPlugin(protection_plugin.ProtectionPlugin):
    def get_protect_operation(self, resource):
        return NoopOperation()

    def get_restore_operation(self, resource):
        return NoopOperation()

    def get_delete_operation(self, resource):
        return NoopOperation()

    @classmethod
    def get_supported_resources_types(cls):
        return constants.RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resource_type):
        return {}

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        return {}

    @classmethod
    def get_restore_schema(cls, resource_type):
        return {}

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        return None
