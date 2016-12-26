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

import mock

from karbor.resource import Resource
from karbor.services.protection import provider
from karbor.tests import base
from karbor.tests.unit.protection import fakes
from oslo_config import cfg

CONF = cfg.CONF

(
    parent_type,
    child_type,
    grandchild_type,
) = fakes.FakeProtectionPlugin.SUPPORTED_RESOURCES

parent = Resource(id='A1', name='parent', type=parent_type)
child = Resource(id='B1', name='child', type=child_type)
grandchild = Resource(id='C1', name='grandchild', type=grandchild_type)
resource_graph = {
    parent: [child],
    child: [grandchild],
    grandchild: [],
}


class ProviderRegistryTest(base.TestCase):
    def setUp(self):
        super(ProviderRegistryTest, self).setUp()

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_bank')
    @mock.patch.object(provider.PluggableProtectionProvider,
                       '_register_plugin')
    def test_load_providers(self, mock_load_bank, mock_register_plugin):
        pr = provider.ProviderRegistry()
        self.assertEqual(mock_register_plugin.call_count, 1)
        self.assertEqual(mock_load_bank.call_count, 1)
        self.assertEqual(len(pr.providers), 1)

        self.assertEqual(pr.providers['fake_id1'].name, 'fake_provider1')
        self.assertNotIn('fake_provider2', pr.providers)

    def test_provider_bank_config(self):
        pr = provider.ProviderRegistry()
        provider1 = pr.show_provider('fake_id1')
        self.assertEqual(provider1.bank._plugin.fake_host, 'thor')

    def test_provider_plugin_config(self):
        pr = provider.ProviderRegistry()
        provider1 = pr.show_provider('fake_id1')
        plugins = provider1.load_plugins()
        self.assertEqual(plugins['Test::ResourceA'].fake_user, 'user')

    def test_list_provider(self):
        pr = provider.ProviderRegistry()
        self.assertEqual(1, len(pr.list_providers()))

    def test_show_provider(self):
        pr = provider.ProviderRegistry()
        provider_list = pr.list_providers()
        for provider_node in provider_list:
            self.assertTrue(pr.show_provider(provider_node['id']))
