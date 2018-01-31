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
from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection import client_factory
from karbor.services.protection.protection_plugins.network \
    import network_plugin_schemas
from karbor.services.protection.protection_plugins.network. \
    neutron_protection_plugin import NeutronProtectionPlugin
from karbor.tests import base
import mock
from oslo_config import cfg

FakeNetworks = {'networks': [
    {u'status': u'ACTIVE',
     u'router:external': False,
     u'availability_zone_hints': [],
     u'availability_zones': [u'nova'],
     u'ipv4_address_scope': None,
     u'description': u'',
     u'provider:physical_network': None,
     u'subnets': [u'129f1bc5-4282-4f9d-ae60-4db1e1cac22d',
                  u'0b42e051-5a33-4ac4-9a4f-691d0891d760'],
     u'updated_at': u'2016-04-23T05:07:06',
     u'tenant_id': u'f6f6d0b2591f41acb8257656d70029fc',
     u'created_at': u'2016-04-23T05:07:06',
     u'tags': [],
     u'ipv6_address_scope': None,
     u'provider:segmentation_id': 1057,
     u'provider:network_type': u'vxlan',
     u'port_security_enabled': True,
     u'admin_state_up': True,
     u'shared': False,
     u'mtu': 1450,
     u'id': u'9b68fb64-39d4-4d41-8cc9-f27846c6e5f5',
     u'name': u'private'},

    {u'provider:physical_network': None,
     u'ipv6_address_scope': None,
     u'port_security_enabled': True,
     u'provider:network_type': u'local',
     u'id': u'49ef013d-9bb2-4b8f-9eea-e45563efc420',
     u'router:external': True,
     u'availability_zone_hints': [],
     u'availability_zones': [u'nova'],
     u'ipv4_address_scope': None,
     u'shared': False,
     u'status': u'ACTIVE',
     u'subnets': [u'808c3b3f-3d79-4c5b-a5b6-95dd07abeb2d'],
     u'description': u'',
     u'tags': [],
     u'updated_at': u'2016-04-25T07:14:53',
     u'is_default': False,
     u'provider:segmentation_id': None,
     u'name': u'ext_net',
     u'admin_state_up': True,
     u'tenant_id': u'f6f6d0b2591f41acb8257656d70029fc',
     u'created_at': u'2016-04-25T07:14:53',
     u'mtu': 1500}
    ]}

FakeSubnets = {'subnets': [
    {u'description': u'',
     u'enable_dhcp': True,
     u'network_id': u'49ef013d-9bb2-4b8f-9eea-e45563efc420',
     u'tenant_id': u'f6f6d0b2591f41acb8257656d70029fc',
     u'created_at': u'2016-04-25T07:15:25',
     u'dns_nameservers': [],
     u'updated_at': u'2016-04-25T07:15:25',
     u'ipv6_ra_mode': None,
     u'allocation_pools': [{u'start': u'192.168.21.2',
                            u'end': u'192.168.21.254'}],
     u'gateway_ip': u'192.168.21.1',
     u'ipv6_address_mode': None,
     u'ip_version': 4,
     u'host_routes': [],
     u'cidr': u'192.168.21.0/24',
     u'id': u'808c3b3f-3d79-4c5b-a5b6-95dd07abeb2d',
     u'subnetpool_id': None,
     u'name': u'ext_subnet'},
    ]}

FakePorts = {'ports': [
    {u'allowed_address_pairs': [],
     u'extra_dhcp_opts': [],
     u'updated_at': u'2016-04-25T07:15:59',
     u'device_owner':
     u'network:router_gateway',
     u'port_security_enabled': False,
     u'binding:profile': {},
     u'fixed_ips': [{u'subnet_id': u'808c3b3f-3d79-4c5b-a5b6-95dd07abeb2d',
                     u'ip_address': u'192.168.21.3'}],
     u'id': u'2b34c97a-4ccc-44c0-bc50-b7bbfc3508eb',
     u'security_groups': [],
     u'binding:vif_details': {},
     u'binding:vif_type': u'unbound',
     u'mac_address': u'fa:16:3e:00:47:f2',
     u'status': u'DOWN',
     u'binding:host_id': u'',
     u'description': u'',
     u'device_id': u'7fc86d4b-4c0e-4ed8-8d39-e27b7c1b7ae8',
     u'name': u'',
     u'admin_state_up': True,
     u'network_id': u'49ef013d-9bb2-4b8f-9eea-e45563efc420',
     u'dns_name': None,
     u'created_at': u'2016-04-25T07:15:59',
     u'binding:vnic_type': u'normal',
     u'tenant_id': u''},
    ]}

FakeRoutes = {'routers': [
    {u'status': u'ACTIVE',
     u'external_gateway_info':
        {u'network_id': u'49ef013d-9bb2-4b8f-9eea-e45563efc420',
         u'enable_snat': True,
         u'external_fixed_ips':
            [{u'subnet_id': u'808c3b3f-3d79-4c5b-a5b6-95dd07abeb2d',
             u'ip_address': u'192.168.21.3'}
             ]},
     u'availability_zone_hints': [],
     u'availability_zones': [],
     u'description': u'',
     u'admin_state_up': True,
     u'tenant_id': u'f6f6d0b2591f41acb8257656d70029fc',
     u'distributed': False,
     u'routes': [],
     u'ha': False,
     u'id': u'7fc86d4b-4c0e-4ed8-8d39-e27b7c1b7ae8',
     u'name': u'provider_route'}
    ]}

FakeSecGroup = {'security_groups': [
    {u'tenant_id': u'23b119d06168447c8dbb4483d9567bd8',
     u'name': u'default',
     u'id': u'97910ed4-1dcb-4704-8814-3ddca818ac16',
     u'description': u'Default security group',
     u'security_group_rules': [
            {u'remote_group_id': u'ac4a6134-0176-44db-abab-559d284c4cdc',
              u'direction': u'ingress',
              u'protocol': None,
              u'description': u'',
              u'ethertype': u'IPv4',
              u'remote_ip_prefix': None,
              u'port_range_max': None,
              u'security_group_id': u'ac4a6134-0176-44db-abab-559d284c4cdc',
              u'port_range_min': None,
              u'tenant_id': u'23b119d06168447c8dbb4483d9567bd8',
              u'id': u'21416a24-6a7a-4830-bbec-1426b21e085a'},

            {u'remote_group_id': u'ac4a6134-0176-44db-abab-559d284c4cdc',
             u'direction': u'ingress',
             u'protocol': None,
             u'description': u'',
             u'ethertype': u'IPv6',
             u'remote_ip_prefix': None,
             u'port_range_max': None,
             u'security_group_id': u'ac4a6134-0176-44db-abab-559d284c4cdc',
             u'port_range_min': None,
             u'tenant_id': u'23b119d06168447c8dbb4483d9567bd8',
             u'id': u'47f67d6a-4e73-465a-9f4d-d9b850f85f22'},

            {u'remote_group_id': None,
             u'direction': u'egress',
             u'protocol': None,
             u'description': u'',
             u'ethertype': u'IPv6',
             u'remote_ip_prefix': None,
             u'port_range_max': None,
             u'security_group_id': u'ac4a6134-0176-44db-abab-559d284c4cdc',
             u'port_range_min': None,
             u'tenant_id': u'23b119d06168447c8dbb4483d9567bd8',
             u'id': u'c24e7148-820c-4147-9032-6fcdb96db6f7'}]},
    ]}


def call_hooks(operation, checkpoint, resource, context, parameters, **kwargs):
    def noop(*args, **kwargs):
        pass

    hooks = (
        'on_prepare_begin',
        'on_prepare_finish',
        'on_main',
        'on_complete',
    )
    for hook_name in hooks:
        hook = getattr(operation, hook_name, noop)
        hook(checkpoint, resource, context, parameters, **kwargs)


class FakeNeutronClient(object):
    def list_networks(self):
        return FakeNetworks

    def list_subnets(self):
        return FakeSubnets

    def list_ports(self):
        return FakePorts

    def list_routers(self):
        return FakeRoutes

    def list_security_groups(self):
        return FakeSecGroup


class FakeBankPlugin(BankPlugin):
    def __init__(self):
        self._objects = {}

    def create_object(self, key, value):
        self._objects[key] = value

    def update_object(self, key, value, context=None):
        self._objects[key] = value

    def get_object(self, key, context=None):
        value = self._objects.get(key, None)
        if value is None:
            raise Exception
        return value

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None, context=None):
        objects_name = []
        if prefix is not None:
            for key, value in self._objects.items():
                if key.find(prefix) == 0:
                    objects_name.append(key.lstrip(prefix))
        else:
            objects_name = self._objects.keys()
        return objects_name

    def delete_object(self, key, context=None):
        self._objects.pop(key)

    def get_owner_id(self, context=None):
        return

fake_checkpointid = "checkpoint_id"
fake_project_id = "abcd"
fake_bank = Bank(FakeBankPlugin())
fake_bank_section = BankSection(bank=fake_bank, section="fake")

ResourceNode = collections.namedtuple(
    "ResourceNode",
    ["value"]
)


class FakeCheckpoint(object):
    def __init__(self):
        self.bank_section = fake_bank_section

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class NeutronProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(NeutronProtectionPluginTest, self).setUp()

        self.plugin = NeutronProtectionPlugin(cfg.CONF)

        cfg.CONF.set_default('neutron_endpoint',
                             'http://127.0.0.1:9696',
                             'neutron_client')

        self.cntxt = RequestContext(user_id='admin',
                                    project_id='abcd',
                                    auth_token='efgh')

        self.neutron_client = client_factory.ClientFactory.create_client(
            "neutron", self.cntxt)
        self.checkpoint = FakeCheckpoint()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            'OS::Neutron::Network')
        self.assertEqual(options_schema,
                         network_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            'OS::Neutron::Network')
        self.assertEqual(options_schema,
                         network_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            'OS::Neutron::Network')
        self.assertEqual(options_schema,
                         network_plugin_schemas.SAVED_INFO_SCHEMA)

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual([constants.NETWORK_RESOURCE_TYPE], types)

    @mock.patch('karbor.services.protection.clients.neutron.create')
    def test_create_backup(self, mock_neutron_create):
        resource = Resource(id="network_id_1",
                            type=constants.NETWORK_RESOURCE_TYPE,
                            name="test")

        fake_bank_section.update_object = mock.MagicMock()

        protect_operation = self.plugin.get_protect_operation(resource)
        mock_neutron_create.return_value = self.neutron_client

        self.neutron_client.list_networks = mock.MagicMock()
        self.neutron_client.list_networks.return_value = FakeNetworks

        self.neutron_client.list_subnets = mock.MagicMock()
        self.neutron_client.list_subnets.return_value = FakeSubnets

        self.neutron_client.list_ports = mock.MagicMock()
        self.neutron_client.list_ports.return_value = FakePorts

        self.neutron_client.list_routers = mock.MagicMock()
        self.neutron_client.list_routers.return_value = FakeRoutes

        self.neutron_client.list_security_groups = mock.MagicMock()
        self.neutron_client.list_security_groups.return_value = FakeSecGroup

        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})

    @mock.patch('karbor.services.protection.clients.neutron.create')
    def test_delete_backup(self, mock_neutron_create):
        resource = Resource(id="network_id_1",
                            type=constants.NETWORK_RESOURCE_TYPE,
                            name="test")

        fake_bank._plugin._objects[
            "/resource_data/checkpoint_id/network_id_1/metadata"] = {
            "resource_id": "network_id_1",
            "network_metadata": {
                "id": "9b68fb64-39d4-4d41-8cc9-f27846c6e5f5",
                "router:external": False,
                "admin_state_up": True,
                "mtu": 1500
            },
            "subnet_metadata": {
                "id": "808c3b3f-3d79-4c5b-a5b6-95dd07abeb2d",
                "network_id": "9b68fb64-39d4-4d41-8cc9-f27846c6e5f5",
                "host_routes": [],
                "dns_nameservers": []
            },
            "port_metadata": {
                "id": "2b34c97a-4ccc-44c0-bc50-b7bbfc3508eb",
                "admin_state_up": True,
                "allowed_address_pairs": [],
                "fixed_ips": [{"subnet_id": "3d79-4c5b-a5b6-95dd07abeb2d",
                               "ip_address": "192.168.21.3"}]
            },
            "router_metadata": {
                "id": "4c0e-4ed8-8d39-e27b7c1b7ae8",
                "admin_state_up": True,
                "availability_zone_hints": [],
                "fixed_ips":  {"network_id": "9bb2-4b8f-9eea-e45563efc420",
                               "enable_snat": True
                               }
            },
            "security-group_metadata": {
                "id": "4ccc-44c0-bc50-b7bbfc3508eb",
                "description": "Default security group",
                "security_group_rules": []
            }
        }

        delete_operation = self.plugin.get_delete_operation(resource)
        mock_neutron_create.return_value = self.neutron_client

        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    @mock.patch('karbor.services.protection.protection_plugins.utils.'
                'update_resource_verify_result')
    def test_verify_backup(self,  mock_update_verify):
        resource = Resource(id="abcd",
                            type=constants.NETWORK_RESOURCE_TYPE,
                            name="test")

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = 'available'

        verify_operation = self.plugin.get_verify_operation(resource)
        call_hooks(verify_operation, self.checkpoint, resource, self.cntxt,
                   {})
        mock_update_verify.assert_called_with(
            None, resource.type, resource.id, 'available')
