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


def set_provider_list(provider_registry):
    provider_registry.providers = {
        'fake_provider_id_1': FakeProvider(
            id='fake_provider_id_1',
            name='fake_provider_name_1',
            description='Fake provider 1 description',
            extended_info_schema=''
        ),
        'fake_provider_id_2': FakeProvider(
            id='fake_provider_id_2',
            name='fake_provider_name_2',
            description='Fake provider 2 description',
            extended_info_schema=''
        )
    }


class FakeProvider(object):
    def __init__(self, id, name, description, extended_info_schema):
        self.id = id
        self.name = name
        self.description = description
        self.extended_info_schema = extended_info_schema


class ProviderRegistryTest(base.TestCase):
    def setUp(self):
        super(ProviderRegistryTest, self).setUp()

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_bank')
    @mock.patch.object(provider.PluggableProtectionProvider,
                       '_register_plugin')
    def test_load_providers(self, mock_register_plugin, mock_load_bank):
        pr = provider.ProviderRegistry()
        self.assertEqual(1, mock_register_plugin.call_count)
        self.assertEqual(1, mock_load_bank.call_count)
        self.assertEqual(1, len(pr.providers))

        self.assertEqual('fake_provider1', pr.providers['fake_id1'].name)
        self.assertNotIn('fake_provider2', pr.providers)

    def test_provider_bank_config(self):
        pr = provider.ProviderRegistry()
        provider1 = pr.show_provider('fake_id1')
        self.assertEqual('thor', provider1.bank._plugin.fake_host)

    def test_provider_plugin_config(self):
        pr = provider.ProviderRegistry()
        provider1 = pr.show_provider('fake_id1')
        plugins = provider1.load_plugins()
        self.assertEqual('user', plugins['Test::ResourceA'].fake_user)

    def test_list_provider(self):
        pr = provider.ProviderRegistry()
        set_provider_list(pr)
        self.assertEqual(2, len(pr.list_providers()))

    def test_list_provider_with_marker(self):
        pr = provider.ProviderRegistry()
        set_provider_list(pr)
        self.assertEqual(
            1, len(pr.list_providers(marker='fake_provider_id_1')))

    def test_list_provider_with_limit(self):
        pr = provider.ProviderRegistry()
        set_provider_list(pr)
        self.assertEqual(
            1, len(pr.list_providers(limit=1)))

    def test_list_provider_with_filters(self):
        pr = provider.ProviderRegistry()
        set_provider_list(pr)
        filters = {'name': 'fake_provider_name_1'}
        self.assertEqual(1, len(pr.list_providers(filters=filters)))

    def test_show_provider(self):
        pr = provider.ProviderRegistry()
        provider_list = pr.list_providers()
        for provider_node in provider_list:
            self.assertTrue(pr.show_provider(provider_node['id']))
