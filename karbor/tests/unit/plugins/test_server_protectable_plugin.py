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
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.protectable_plugins.server \
    import ServerProtectablePlugin

from karbor.tests import base
import mock
from novaclient.v2 import servers
from oslo_config import cfg


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
        self.assertEqual('compute',
                         plugin._client(self._context).client.service_type)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         plugin._client(self._context).client.management_url)

    def test_create_client_by_catalog(self):
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual('compute',
                         plugin._client(self._context).client.service_type)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         plugin._client(self._context).client.management_url)

    def test_get_resource_type(self):
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual("OS::Nova::Server", plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = ServerProtectablePlugin(self._context)
        self.assertEqual(("OS::Keystone::Project", ),
                         plugin.get_parent_resource_types())

    @mock.patch.object(servers.ServerManager, 'list')
    def test_list_resources(self, mock_server_list):
        plugin = ServerProtectablePlugin(self._context)

        server_info = collections.namedtuple('server_info', ['id', 'name'])
        mock_server_list.return_value = [
            server_info(id='123', name='name123'),
            server_info(id='456', name='name456')]
        self.assertEqual([Resource('OS::Nova::Server', '123', 'name123'),
                          Resource('OS::Nova::Server', '456', 'name456')],
                         plugin.list_resources(self._context))

    @mock.patch.object(servers.ServerManager, 'get')
    def test_show_resource(self, mock_server_get):
        plugin = ServerProtectablePlugin(self._context)

        server_info = collections.namedtuple('server_info', ['id', 'name'])
        mock_server_get.return_value = \
            server_info(id='123', name='name123')
        self.assertEqual(Resource('OS::Nova::Server', '123', 'name123'),
                         plugin.show_resource(self._context, '123'))

    @mock.patch.object(servers.ServerManager, 'list')
    def test_get_dependent_resources(self, mock_server_list):
        plugin = ServerProtectablePlugin(self._context)

        server_info = collections.namedtuple('server_info', ['id', 'name'])
        mock_server_list.return_value = [
            server_info(id='123', name='name123'),
            server_info(id='456', name='name456')]
        self.assertEqual([Resource('OS::Nova::Server', '123', 'name123'),
                          Resource('OS::Nova::Server', '456', 'name456')],
                         plugin.get_dependent_resources(self._context, None))
