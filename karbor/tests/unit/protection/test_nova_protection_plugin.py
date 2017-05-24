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

from collections import namedtuple
from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection.protection_plugins.server \
    import server_plugin_schemas
from karbor.services.protection.protection_plugins.server. \
    nova_protection_plugin import NovaProtectionPlugin
from karbor.tests import base
import mock


class Server(object):
    def __init__(self, id, addresses, availability_zone,
                 flavor, key_name, security_groups):
        super(Server, self).__init__()
        self.id = id
        self.addresses = addresses
        self.__setattr__("OS-EXT-AZ:availability_zone", availability_zone)
        self.flavor = flavor
        self.key_name = key_name
        self.security_groups = security_groups


class Volume(object):
    def __init__(self, id, volume_type, status, bootable,
                 attachments, name=None):
        super(Volume, self).__init__()
        self.id = id
        self.volume_type = volume_type
        self.status = status
        self.bootable = bootable
        self.attachments = attachments
        self.name = name


class Image(object):
    def __init__(self, id, status, disk_format, container_format):
        super(Image, self).__init__()
        self.id = id
        self.status = status
        self.disk_format = disk_format
        self.container_format = container_format


FakePorts = {'ports': [
    {'fixed_ips': [{'subnet_id': 'subnet-1',
                    'ip_address': '10.0.0.21'}],
     'id': 'port-1',
     'mac_address': 'mac_address_1',
     'device_id': 'vm_id_1',
     'name': '',
     'admin_state_up': True,
     'network_id': 'network_id_1'},
    {'fixed_ips': [{'subnet_id': 'subnet-1',
                    'ip_address': '10.0.0.22'}],
     'id': 'port-2',
     'mac_address': 'mac_address_2',
     'device_id': 'vm_id_2',
     'name': '',
     'admin_state_up': True,
     'network_id': 'network_id_2'}
]}

FakeServers = {
    "vm_id_1": Server(id="vm_id_1",
                      addresses={'fake_net': [
                          {'OS-EXT-IPS-MAC:mac_addr': 'mac_address_1',
                           'OS-EXT-IPS:type': 'fixed',
                           'addr': '10.0.0.21',
                           'version': 4}
                      ]},
                      availability_zone="nova",
                      flavor={'id': 'flavor_id',
                              'links': [
                                  {'href': '',
                                   'rel': 'bookmark'}
                              ]},
                      key_name=None,
                      security_groups="default"),
    "vm_id_2": Server(id="vm_id_2",
                      addresses={'fake_net': [
                          {'OS-EXT-IPS-MAC:mac_addr': 'mac_address_2',
                           'OS-EXT-IPS:type': 'fixed',
                           'addr': '10.0.0.22',
                           'version': 4}
                      ]},
                      availability_zone="nova",
                      flavor={'id': 'flavor_id',
                              'links': [
                                  {'href': '',
                                   'rel': 'bookmark'}
                              ]},
                      key_name=None,
                      security_groups="default")
}

FakeVolumes = {
    "vol_id_1": Volume(id="vol_id_1",
                       volume_type="",
                       status="in-use",
                       bootable="",
                       attachments=[{'server_id': 'vm_id_2',
                                     'attachment_id': '',
                                     'host_name': '',
                                     'volume_id': 'vol_id_1',
                                     'device': '/dev/vdb',
                                     'id': 'attach_id_1'}],
                       name="vol_id_1_name")
}

FakeImages = {
    "image_id_1": Image(id="image_id_1",
                        disk_format="",
                        container_format="",
                        status="active")
}

FakeGraphNode = namedtuple("GraphNode", (
    "value",
    "child_nodes",
))


class FakeNovaClient(object):
    class Servers(object):
        def get(self, server_id):
            return FakeServers[server_id]

        def create_image(self, server_id, name, **kwargs):
            FakeImages["image_id_2"] = Image(id="image_id_2",
                                             disk_format="",
                                             container_format="",
                                             status="active")
            return "image_id_2"

        def __getattr__(self, item):
            return None

    def __init__(self):
        super(FakeNovaClient, self).__init__()
        self.servers = self.Servers()


class FakeGlanceClient(object):
    class Images(object):
        def get(self, image_id):
            return FakeImages[image_id]

        def data(self, image_id):
            return "image_data_" + image_id

        def delete(self, image_id):
            if image_id in FakeImages:
                FakeImages.pop(image_id)

        def __getattr__(self, item):
            return None

    def __init__(self):
        super(FakeGlanceClient, self).__init__()
        self.images = self.Images()


class FakeCinderClient(object):
    class Volumes(object):
        def get(self, volume_id):
            return FakeVolumes[volume_id]

        def list(self, detailed=True, search_opts=None, limit=None):
            return [FakeVolumes['vol_id_1'], ]

        def __getattr__(self, item):
            return None

    def __init__(self):
        super(FakeCinderClient, self).__init__()
        self.volumes = self.Volumes()


class FakeNeutronClient(object):
    def list_ports(self, mac_address):
        result_ports = []
        for port in FakePorts["ports"]:
            if port["mac_address"] == mac_address:
                result_ports.append(port)
        return {"ports": result_ports}


class FakeBankPlugin(BankPlugin):
    def __init__(self, config=None):
        super(FakeBankPlugin, self).__init__(config)
        self._objects = {}

    def update_object(self, key, value):
        self._objects[key] = value

    def get_object(self, key):
        value = self._objects.get(key, None)
        if value is None:
            raise Exception
        return value

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        objects_name = []
        if prefix is not None:
            for key, value in self._objects.items():
                if key.find(prefix) == 0:
                    objects_name.append(key)
        else:
            objects_name = self._objects.keys()
        return objects_name

    def delete_object(self, key):
        self._objects.pop(key)

    def get_owner_id(self):
        return


fake_bank = Bank(FakeBankPlugin())

ResourceNode = collections.namedtuple(
    "ResourceNode",
    ["value",
     "child_nodes"]
)


class Checkpoint(object):
    def __init__(self):
        super(Checkpoint, self).__init__()
        self.id = "checkpoint_id"
        self.graph = []

    @property
    def resource_graph(self):
        return self.graph

    @resource_graph.setter
    def resource_graph(self, resource_graph):
        self.graph = resource_graph

    def get_resource_bank_section(self, resource_id):
        return BankSection(
            bank=fake_bank,
            section="/resource_data/%s/%s" % (self.id, resource_id)
        )


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


class NovaProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(NovaProtectionPluginTest, self).setUp()
        self.cntxt = RequestContext(user_id='demo',
                                    project_id='abcd',
                                    auth_token='efgh')
        self.plugin = NovaProtectionPlugin()
        self.glance_client = FakeGlanceClient()
        self.nova_client = FakeNovaClient()
        self.cinder_client = FakeCinderClient()
        self.neutron_client = FakeNeutronClient()
        self.checkpoint = Checkpoint()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            constants.SERVER_RESOURCE_TYPE)
        self.assertEqual(options_schema, server_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            constants.SERVER_RESOURCE_TYPE)
        self.assertEqual(options_schema, server_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            constants.SERVER_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         server_plugin_schemas.SAVED_INFO_SCHEMA)

    @mock.patch('karbor.services.protection.clients.neutron.create')
    @mock.patch('karbor.services.protection.clients.glance.create')
    @mock.patch('karbor.services.protection.clients.nova.create')
    @mock.patch('karbor.services.protection.clients.cinder.create')
    def test_create_backup_without_volumes(self, mock_cinder_client,
                                           mock_nova_client,
                                           mock_glance_client,
                                           mock_neutron_client):
        resource = Resource(id="vm_id_1",
                            type=constants.SERVER_RESOURCE_TYPE,
                            name="fake_vm")

        protect_operation = self.plugin.get_protect_operation(resource)
        mock_cinder_client.return_value = self.cinder_client
        mock_nova_client.return_value = self.nova_client
        mock_glance_client.return_value = self.glance_client
        mock_neutron_client.return_value = self.neutron_client

        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})

        self.assertEqual(
            constants.RESOURCE_STATUS_AVAILABLE,
            fake_bank._plugin._objects[
                "/resource_data/checkpoint_id/vm_id_1/status"]
        )
        resource_definition = {
            "resource_id": "vm_id_1",
            "attach_metadata": {},
            'boot_metadata': {'boot_device_type': 'volume'},
            "server_metadata": {
                "availability_zone": "nova",
                "networks": ["network_id_1"],
                "floating_ips": [],
                "flavor": "flavor_id",
                "key_name": None,
                "security_groups": "default",
            },
        }
        self.assertEqual(
            resource_definition,
            fake_bank._plugin._objects[
                "/resource_data/checkpoint_id/vm_id_1/metadata"]
        )

    @mock.patch('karbor.services.protection.clients.neutron.create')
    @mock.patch('karbor.services.protection.clients.glance.create')
    @mock.patch('karbor.services.protection.clients.nova.create')
    @mock.patch('karbor.services.protection.clients.cinder.create')
    def test_create_backup_with_volumes(self, mock_cinder_client,
                                        mock_nova_client,
                                        mock_glance_client,
                                        mock_neutron_client):
        vm_resource = Resource(id="vm_id_2",
                               type=constants.SERVER_RESOURCE_TYPE,
                               name="fake_vm")

        protect_operation = self.plugin.get_protect_operation(vm_resource)
        mock_cinder_client.return_value = self.cinder_client
        mock_nova_client.return_value = self.nova_client
        mock_glance_client.return_value = self.glance_client
        mock_neutron_client.return_value = self.neutron_client
        checkpoint = Checkpoint()
        checkpoint.resource_graph = [FakeGraphNode(value=Resource(
            type='OS::Nova::Server', id='vm_id_2', name='None'),
            child_nodes=[FakeGraphNode(value=Resource(
                type='OS::Cinder::Volume', id='vol_id_1', name=None),
                child_nodes=())])]

        call_hooks(protect_operation, checkpoint, vm_resource, self.cntxt,
                   {})

        self.assertEqual(
            fake_bank._plugin._objects[
                "/resource_data/checkpoint_id/vm_id_2/status"],
            constants.RESOURCE_STATUS_AVAILABLE
        )
        resource_definition = {
            "resource_id": "vm_id_2",
            "attach_metadata": {"vol_id_1": "/dev/vdb"},
            'boot_metadata': {'boot_device_type': 'volume'},
            "server_metadata": {
                "availability_zone": "nova",
                "networks": ["network_id_2"],
                "floating_ips": [],
                "flavor": "flavor_id",
                "key_name": None,
                "security_groups": "default",
            },
            'attach_metadata': {
                'vol_id_1': {'attachment_id': '',
                             'bootable': '',
                             'device': '/dev/vdb',
                             'host_name': '',
                             'id': 'attach_id_1',
                             'server_id': 'vm_id_2',
                             'volume_id': 'vol_id_1'}
            },
        }
        self.assertEqual(
            fake_bank._plugin._objects[
                "/resource_data/checkpoint_id/vm_id_2/metadata"],
            resource_definition
        )

    @mock.patch('karbor.services.protection.clients.glance.create')
    def test_delete_backup(self, mock_glance_client):
        resource = Resource(id="vm_id_1",
                            type=constants.SERVER_RESOURCE_TYPE,
                            name="fake_vm")

        fake_bank._plugin._objects[
            "/resource_data/checkpoint_id/vm_id_1/metadata"] = {
            "resource_id": "vm_id_1",
            "attach_metadata": {},
            "server_metadata": {
                "availability_zone": "nova",
                "networks": ["network_id_1"],
                "floating_ips": [],
                "flavor": "flavor_id",
                "key_name": None,
                "security_groups": "default",
            },
            "snapshot_id": "image_id_2",
            "snapshot_metadata": {
                "disk_format": "",
                "container_format": "",
                "name": "snapshot_checkpoint_id@vm_id_1"
            }
        }

        delete_operation = self.plugin.get_delete_operation(resource)
        mock_glance_client.return_value = self.glance_client

        fake_bank._plugin._objects[
            "/resource_data/checkpoint_id/vm_id_1/data_0"
        ] = "image_data_1"
        fake_bank._plugin._objects[
            "/resource_data/checkpoint_id/vm_id_1/data_1"
        ] = "image_data_1"

        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.SERVER_RESOURCE_TYPE])
