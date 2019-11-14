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

import mock


from karbor.common import karbor_keystone_plugin
from karbor.tests import base

from oslo_config import cfg
from oslo_config import fixture


class KarborKeystonePluginTest(base.TestCase):

    def setUp(self):
        super(KarborKeystonePluginTest, self).setUp()
        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='trustee',
            poll_interval=0,
        )
        cfg.CONF.set_default('project_name',
                             'services',
                             "trustee")
        self.kc_plugin = karbor_keystone_plugin.KarborKeystonePlugin()
        self.kc_plugin.client.services.list = mock.MagicMock()
        self.kc_plugin.client.endpoints.list = mock.MagicMock()
        self.kc_plugin.client.services.list.return_value = (
            'http://192.168.1.2:8799')

    def test_get_service_endpoint_with_slash_end(self):
        self.kc_plugin._auth_uri = 'http://192.168.1.1/identity/v3/'
        self.kc_plugin.get_service_endpoint(
            'karbor', 'data-protect', 'fake_region_id', 'public')
        self.kc_plugin.client.services.list.assert_called_once_with(
            name='karbor',
            service_type='data-protect',
            base_url='http://192.168.1.1/identity/v3'
        )

    def test_get_service_endpoint_with_no_slash_end(self):
        self.kc_plugin._auth_uri = 'http://192.168.1.1/identity/v3'
        self.kc_plugin.get_service_endpoint(
            'karbor', 'data-protect', 'fake_region_id', 'public')
        self.kc_plugin.client.services.list.assert_called_once_with(
            name='karbor',
            service_type='data-protect',
            base_url='http://192.168.1.1/identity/v3'
        )

    def test_service_auth_plugin_with_project_name(self):
        self.assertEqual(self.kc_plugin.service_auth_plugin._project_name,
                         'services')
