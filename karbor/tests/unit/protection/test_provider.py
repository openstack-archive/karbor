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

from karbor.services.protection import provider
from karbor.tests import base
import mock

from oslo_config import cfg

CONF = cfg.CONF


class ProviderRegistryTest(base.TestCase):
    def setUp(self):
        super(ProviderRegistryTest, self).setUp()

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_bank')
    @mock.patch.object(provider.PluggableProtectionProvider, '_load_plugin')
    def test_load_providers(self, mock_load_bank, mock_load_plugin):
        pr = provider.ProviderRegistry()
        self.assertEqual(mock_load_plugin.call_count, 1)
        self.assertEqual(mock_load_bank.call_count, 1)
        self.assertEqual(len(pr.providers), 1)

        self.assertEqual(pr.providers['fake_id1'].name, 'fake_provider1')
        self.assertNotIn('fake_provider2', pr.providers)

    def test_provider_bank_config(self):
        pr = provider.ProviderRegistry()
        provider1 = pr.show_provider('fake_id1')
        self.assertEqual(provider1.bank._plugin._config.fake_bank.fake_host,
                         'thor')

    def test_provider_plugin_config(self):
        pr = provider.ProviderRegistry()
        provider1 = pr.show_provider('fake_id1')
        plugin_name = 'karbor.tests.unit.fake_protection.FakeProtectionPlugin'
        self.assertEqual(
            provider1.plugins[plugin_name]._config.fake_plugin.fake_user,
            'user')

    def test_list_provider(self):
        pr = provider.ProviderRegistry()
        self.assertEqual(1, len(pr.list_providers()))

    def test_show_provider(self):
        pr = provider.ProviderRegistry()
        provider_list = pr.list_providers()
        for provider_node in provider_list:
            self.assertTrue(pr.show_provider(provider_node['id']))
