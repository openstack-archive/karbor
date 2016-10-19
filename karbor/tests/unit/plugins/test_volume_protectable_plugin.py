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

from cinderclient.v3 import volumes
from collections import namedtuple
import mock

from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.protectable_plugins.volume \
    import VolumeProtectablePlugin

from karbor.tests import base
from oslo_config import cfg

project_info = namedtuple('project_info', field_names=['id', 'type', 'name'])
vol_info = namedtuple('vol_info', ['id', 'attachments', 'name', 'status',
                                   'availability_zone'])


class VolumeProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(VolumeProtectablePluginTest, self).setUp()
        service_catalog = [
            {'type': 'volumev3',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8776/v3/abcd'}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('cinder_endpoint',
                             'http://127.0.0.1:8776/v3',
                             'cinder_client')
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual('volumev3',
                         plugin._client(self._context).client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v3/abcd',
                         plugin._client(self._context).client.management_url)

    def test_create_client_by_catalog(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual('volumev3',
                         plugin._client(self._context).client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v3/abcd',
                         plugin._client(self._context).client.management_url)

    def test_get_resource_type(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual("OS::Cinder::Volume", plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertItemsEqual(("OS::Nova::Server", "OS::Keystone::Project"),
                              plugin.get_parent_resource_types())

    @mock.patch.object(volumes.VolumeManager, 'list')
    def test_list_resources(self, mock_volume_list):
        plugin = VolumeProtectablePlugin(self._context)
        mock_volume_list.return_value = [
            vol_info('123', [], 'name123', 'available', 'az1'),
            vol_info('456', [], 'name456', 'available', 'az1'),
        ]
        self.assertEqual([Resource('OS::Cinder::Volume', '123', 'name123',
                                   {'availability_zone': 'az1'}),
                          Resource('OS::Cinder::Volume', '456', 'name456',
                                   {'availability_zone': 'az1'})],
                         plugin.list_resources(self._context))

    @mock.patch.object(volumes.VolumeManager, 'get')
    def test_show_resource(self, mock_volume_get):
        plugin = VolumeProtectablePlugin(self._context)

        vol_info = namedtuple('vol_info', ['id', 'name', 'status',
                              'availability_zone'])
        mock_volume_get.return_value = vol_info(id='123', name='name123',
                                                status='available',
                                                availability_zone='az1')
        self.assertEqual(Resource('OS::Cinder::Volume', '123', 'name123',
                                  {'availability_zone': 'az1'}),
                         plugin.show_resource(self._context, "123"))

    @mock.patch.object(volumes.VolumeManager, 'list')
    def test_get_server_dependent_resources(self, mock_volume_list):
        plugin = VolumeProtectablePlugin(self._context)

        attached = [{'server_id': 'abcdef', 'name': 'name'}]
        mock_volume_list.return_value = [
            vol_info('123', attached, 'name123', 'available', 'az1'),
            vol_info('456', [], 'name456', 'available', 'az1'),
        ]
        self.assertEqual([Resource('OS::Cinder::Volume', '123', 'name123',
                                   {'availability_zone': 'az1'})],
                         plugin.get_dependent_resources(
                             self._context,
                             Resource("OS::Nova::Server", 'abcdef', 'name',
                                      {'availability_zone': 'az1'})))

    @mock.patch.object(volumes.VolumeManager, 'list')
    def test_get_project_dependent_resources(self, mock_volume_list):
        project = project_info('abcd', constants.PROJECT_RESOURCE_TYPE,
                               'nameabcd')
        plugin = VolumeProtectablePlugin(self._context)

        volumes = [
            mock.Mock(name='Volume', id='123', availability_zone='az1'),
            mock.Mock(name='Volume', id='456', availability_zone='az1'),
        ]
        setattr(volumes[0], 'os-vol-tenant-attr:tenant_id', 'abcd')
        setattr(volumes[1], 'os-vol-tenant-attr:tenant_id', 'efgh')
        setattr(volumes[0], 'name', 'name123')
        setattr(volumes[1], 'name', 'name456')

        mock_volume_list.return_value = volumes
        self.assertEqual(
            plugin.get_dependent_resources(self._context, project),
            [Resource('OS::Cinder::Volume', '123', 'name123',
                      {'availability_zone': 'az1'})])
