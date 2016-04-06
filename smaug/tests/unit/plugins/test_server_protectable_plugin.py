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

import collections
import mock

from oslo_config import cfg
from smaug.context import RequestContext
from smaug.resource import Resource
from smaug.services.protection.protectable_plugins.server \
    import ServerProtectablePlugin

from smaug.tests import base


class ServerProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(ServerProtectablePluginTest, self).setUp()
        service_catalog = [
            {'type': 'compute',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8774/v2.1/abcd'}],
             },
        ]
        self._context = RequestContext(user_id='admin',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('nova_endpoint',
                             'http://127.0.0.1:8774/v2.1',
                             'nova_client')
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual('compute', plugin._client.client.service_type)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         plugin._client.client.management_url)

    def test_create_client_by_catalog(self):
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual('compute', plugin._client.client.service_type)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         plugin._client.client.management_url)

    def test_get_resource_type(self):
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual("OS::Nova::Server", plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual(("OS::Keystone::Project", ),
                         plugin.get_parent_resource_types())

    def test_list_resources(self):
        plugin = ServerProtectablePlugin(self._context)
        plugin._client.servers.list = mock.MagicMock()

        server_info = collections.namedtuple('server_info', ['id', 'name'])
        plugin._client.servers.list.return_value = [
            server_info(id='123', name='name123'),
            server_info(id='456', name='name456')]
        self.assertEqual([Resource('OS::Nova::Server', '123', 'name123'),
                          Resource('OS::Nova::Server', '456', 'name456')],
                         plugin.list_resources())

    def test_get_dependent_resources(self):
        plugin = ServerProtectablePlugin(self._context)
        plugin._client.servers.list = mock.MagicMock()

        server_info = collections.namedtuple('server_info', ['id', 'name'])
        plugin._client.servers.list.return_value = [
            server_info(id='123', name='name123'),
            server_info(id='456', name='name456')]
        self.assertEqual([Resource('OS::Nova::Server', '123', 'name123'),
                          Resource('OS::Nova::Server', '456', 'name456')],
                         plugin.get_dependent_resources(None))
