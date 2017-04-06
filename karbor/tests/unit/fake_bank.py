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

from oslo_config import cfg

from karbor.services.protection import bank_plugin

fake_bank_opts = [
    cfg.HostAddressOpt('fake_host'),
]


class FakeBankPlugin(bank_plugin.BankPlugin):
    def __init__(self, config=None):
        super(FakeBankPlugin, self).__init__(config)
        config.register_opts(fake_bank_opts, 'fake_bank')
        self.fake_host = config['fake_bank']['fake_host']

    def update_object(self, key, value):
        return

    def get_object(self, key):
        return

    def list_objects(self, prefix=None, limit=None,
                     marker=None, sort_dir=None):
        return

    def delete_object(self, key):
        return

    def get_owner_id(self):
        return
