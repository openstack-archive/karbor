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
from oslo_config import cfg
from smaug.services.protection import provider
from smaug.tests import base

provider_opt = [
    cfg.MultiStrOpt('plugin',
                    default='',
                    help='plugins to use for protection'),
    cfg.StrOpt('description',
               default='',
               help='the description of provider'),
    cfg.StrOpt('provider_id',
               default='',
               help='the provider id')
]
CONF = cfg.CONF


class ProviderRegistryTest(base.TestCase):
    def setUp(self):
        super(ProviderRegistryTest, self).setUp()
        CONF.set_override('enabled_providers',
                          ['provider1', 'provider2'])
        CONF.register_opts(provider_opt, group='provider1')
        CONF.register_opts(provider_opt, group='provider2')
        CONF.set_override('plugin', ['SERVER', 'VOLUME'],
                          group='provider1')
        CONF.set_override('plugin', ['SERVER'],
                          group='provider2')
        CONF.set_override('description', 'FAKE1', group='provider1')
        CONF.set_override('description', 'FAKE2', group='provider2')
        CONF.set_override('provider_id', 'id1', group='provider1')
        CONF.set_override('provider_id', 'id2', group='provider2')

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_plugins')
    def test_load_providers(self, mock_load_plugins):
        CONF.set_override('plugin', ['SERVER'],
                          group='provider2')
        pr = provider.ProviderRegistry()
        self.assertTrue(mock_load_plugins.called)
        self.assertEqual(len(pr.providers), 2)

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_plugins')
    def test_load_providers_with_no_plugins(self, mock_load_plugins):
        CONF.set_override('plugin', None,
                          group='provider2')
        pr = provider.ProviderRegistry()
        self.assertEqual(mock_load_plugins.call_count, 1)
        self.assertEqual(len(pr.providers), 1)

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_plugins')
    def test_list_provider(self, mock_load_plugins):
        CONF.set_override('plugin', ['SERVER'],
                          group='provider2')
        pr = provider.ProviderRegistry()
        self.assertEqual(2, len(pr.list_providers()))

    @mock.patch.object(provider.PluggableProtectionProvider, '_load_plugins')
    def test_show_provider(self, mock_load_plugins):
        CONF.set_override('plugin', ['SERVER'],
                          group='provider2')
        pr = provider.ProviderRegistry()
        provider_list = pr.list_providers()
        for provider_node in provider_list:
            self.assertTrue(pr.show_provider(provider_node['id']))

    def tearDown(self):
        CONF.register_opts(provider_opt, group='provider1')
        CONF.register_opts(provider_opt, group='provider2')
        CONF.set_override('enabled_providers',
                          None)
        super(ProviderRegistryTest, self).tearDown()
