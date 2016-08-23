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

from oslo_config import cfg

from karbor.services.protection import protection_plugin

fake_plugin_opts = [
    cfg.StrOpt('fake_user'),
]


class FakeProtectionPlugin(protection_plugin.ProtectionPlugin):
    def __init__(self, config=None):
        super(FakeProtectionPlugin, self).__init__(config)
        config.register_opts(fake_plugin_opts, 'fake_plugin')

    def get_supported_resources_types(self):
        return ['Test::Resource']

    def get_options_schema(self, resource_type):
        return []

    def get_saved_info_schema(self, resource_type):
        return []

    def get_restore_schema(self, resource_type):
        return []

    def get_saved_info(self, metadata_store, resource):
        pass

    def get_resource_stats(self, checkpoint, resource_id):
        pass

    def on_resource_start(self, context):
        pass

    def on_resource_end(self, context):
        pass
