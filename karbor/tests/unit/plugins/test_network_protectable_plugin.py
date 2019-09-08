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

from collections import namedtuple
import mock

from karbor.common import constants
from karbor.context import RequestContext
from karbor import resource
from karbor.services.protection.protectable_plugins.network import \
    NetworkProtectablePlugin
from karbor.tests import base
from keystoneauth1 import session as keystone_session
from neutronclient.v2_0 import client
from oslo_config import cfg

CONF = cfg.CONF

server_info = namedtuple('server_info',
                         field_names=['id', 'type', 'name', 'addresses'])
project_info = namedtuple('project_info', field_names=['id', 'type'])

FakePorts = {'ports': [
    {'fixed_ips': [{'subnet_id': 'subnet-1',
                    'ip_address': '10.0.0.21'}],
     'id': 'port-1',
     'mac_address': 'mac_address_1',
     'device_id': 'vm_id_1',
     'name': '',
     'admin_state_up': True,
     'network_id': '658e1063-4ee3-4649-a2c9'},
    {'fixed_ips': [{'subnet_id': 'subnet-1',
                    'ip_address': '10.0.0.22'}],
     'id': 'port-2',
     'mac_address': 'mac_address_2',
     'device_id': 'vm_id_2',
     'name': '',
     'admin_state_up': True,
     'network_id': 'network_id_2'}
]}


class NetworkProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(NetworkProtectablePluginTest, self).setUp()

        service_catalog = [{
            'type': 'network',
            'endpoints': [{'publicURL': 'http://127.0.0.1:9696'}]
        }, {
            'type': 'compute',
            'endpoints': [{'publicURL': 'http://127.0.0.1:8774/v2.1/abcd'}]
        }]
        self._context = RequestContext(user_id='admin',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_create_client_by_endpoint(self, mock_generate_session):
        CONF.set_default('neutron_endpoint', 'http://127.0.0.1:9696',
                         'neutron_client')
        CONF.set_default('nova_endpoint', 'http://127.0.0.1:8774/v2.1',
                         'nova_client')
        plugin = NetworkProtectablePlugin(self._context)
        neutronclient = plugin._neutron_client(self._context)
        novaclient = plugin._nova_client(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual('network',
                         neutronclient.httpclient.service_type)
        self.assertEqual('http://127.0.0.1:9696',
                         neutronclient.httpclient.endpoint_url)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         novaclient.client.endpoint_override)

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_create_client_by_catalog(self, mock_generate_session):
        CONF.set_default('neutron_catalog_info', 'network:neutron:publicURL',
                         'neutron_client')
        CONF.set_default('nova_catalog_info', 'compute:nova:publicURL',
                         'nova_client')
        plugin = NetworkProtectablePlugin(self._context)
        neutronclient = plugin._neutron_client(self._context)
        novaclient = plugin._nova_client(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual('network',
                         neutronclient.httpclient.service_type)
        self.assertEqual('http://127.0.0.1:9696',
                         neutronclient.httpclient.endpoint_url)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         novaclient.client.endpoint_override)

    def test_get_resource_type(self):
        plugin = NetworkProtectablePlugin(self._context)
        self.assertEqual(constants.NETWORK_RESOURCE_TYPE,
                         plugin.get_resource_type())

    def test_get_parent_resource_type(self):
        plugin = NetworkProtectablePlugin(self._context)
        self.assertItemsEqual(plugin.get_parent_resource_types(),
                              (constants.PROJECT_RESOURCE_TYPE))

    @mock.patch.object(client.Client, 'list_networks')
    def test_list_resources(self, mock_client_list_networks):
        plugin = NetworkProtectablePlugin(self._context)

        fake_network_info = {'networks': [
            {u'status': u'ACTIVE',
             u'description': u'',
             u'tenant_id': u'abcd',
             u'name': u'private'},
            {u'status': u'ACTIVE',
             u'description': u'',
             u'name': u'ext_net',
             u'tenant_id': u'abcd'}
            ]}

        mock_client_list_networks.return_value = fake_network_info
        self.assertEqual(plugin.list_resources(self._context),
                         [resource.Resource
                             (type=constants.NETWORK_RESOURCE_TYPE,
                              id='abcd',
                              name="Network Topology")])

    @mock.patch.object(client.Client, 'list_networks')
    def test_get_project_dependent_resources(self, mock_client_list_networks):
        project = project_info(id='abcd',
                               type=constants.PROJECT_RESOURCE_TYPE)
        plugin = NetworkProtectablePlugin(self._context)
        fake_network_info = {'networks': [
            {u'status': u'ACTIVE',
             u'description': u'',
             u'tenant_id': u'abcd',
             u'name': u'private'},
            {u'status': u'ACTIVE',
             u'description': u'',
             u'name': u'ext_net',
             u'tenant_id': u'abcd'}
            ]}
        mock_client_list_networks.return_value = fake_network_info
        self.assertEqual(plugin.get_dependent_resources(self._context,
                                                        project),
                         [resource.Resource
                             (type=constants.NETWORK_RESOURCE_TYPE,
                              id='abcd',
                              name="Network Topology")])
