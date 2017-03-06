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
from keystoneauth1 import session as keystone_session
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
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_create_client_by_endpoint(self, mock_generate_session):
        cfg.CONF.set_default('nova_endpoint',
                             'http://127.0.0.1:8774/v2.1',
                             'nova_client')
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual('compute',
                         plugin._client(self._context).client.service_type)
        self.assertEqual(
            'http://127.0.0.1:8774/v2.1/abcd',
            plugin._client(self._context).client.endpoint_override)

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_create_client_by_catalog(self, mock_generate_session):
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual('compute',
                         plugin._client(self._context).client.service_type)
        self.assertEqual(
            'http://127.0.0.1:8774/v2.1/abcd',
            plugin._client(self._context).client.endpoint_override)

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_get_resource_type(self, mock_generate_session):
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual("OS::Nova::Server", plugin.get_resource_type())

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_get_parent_resource_types(self, mock_generate_session):
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual(("OS::Keystone::Project", ),
                         plugin.get_parent_resource_types())

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    @mock.patch.object(servers.ServerManager, 'list')
    def test_list_resources(self, mock_server_list, mock_generate_session):
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)

        server_info = collections.namedtuple('server_info', ['id', 'name',
                                                             'status'])
        mock_server_list.return_value = [
            server_info(id='123', name='name123', status='ACTIVE'),
            server_info(id='456', name='name456', status='ACTIVE')]
        self.assertEqual([Resource('OS::Nova::Server', '123', 'name123'),
                          Resource('OS::Nova::Server', '456', 'name456')],
                         plugin.list_resources(self._context))

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    @mock.patch.object(servers.ServerManager, 'get')
    def test_show_resource(self, mock_server_get, mock_generate_session):
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)

        server_info = collections.namedtuple('server_info', ['id', 'name',
                                                             'status'])
        mock_server_get.return_value = server_info(id='123', name='name123',
                                                   status='ACTIVE')
        self.assertEqual(Resource('OS::Nova::Server', '123', 'name123'),
                         plugin.show_resource(self._context, '123'))

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    @mock.patch.object(servers.ServerManager, 'list')
    def test_get_dependent_resources(self, mock_server_list,
                                     mock_generate_session):
        plugin = ServerProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)

        server_info = collections.namedtuple('server_info', ['id', 'name',
                                                             'status'])
        mock_server_list.return_value = [
            server_info(id='123', name='name123', status='ACTIVE'),
            server_info(id='456', name='name456', status='ACTIVE')]
        self.assertEqual([Resource('OS::Nova::Server', '123', 'name123'),
                          Resource('OS::Nova::Server', '456', 'name456')],
                         plugin.get_dependent_resources(self._context, None))
