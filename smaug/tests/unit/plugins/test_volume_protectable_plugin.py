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

from oslo_config import cfg
from smaug.common import constants
from smaug.context import RequestContext
from smaug.resource import Resource
from smaug.services.protection.protectable_plugins.volume \
    import VolumeProtectablePlugin

from smaug.tests import base

project_info = namedtuple('project_info', field_names=['id', 'type', 'name'])
vol_info = namedtuple('vol_info', ['id', 'attachments', 'name'])


class VolumeProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(VolumeProtectablePluginTest, self).setUp()
        service_catalog = [
            {'type': 'volumev2',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8776/v2/abcd'}],
             },
        ]
        self._context = RequestContext(user_id='admin',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('cinder_endpoint',
                             'http://127.0.0.1:8776/v2',
                             'cinder_client')
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual('volumev2', plugin._client.client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v2/abcd',
                         plugin._client.client.management_url)

    def test_create_client_by_catalog(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual('volumev2', plugin._client.client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v2/abcd',
                         plugin._client.client.management_url)

    def test_get_resource_type(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual("OS::Cinder::Volume", plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertItemsEqual(("OS::Nova::Server", "OS::Keystone::Project"),
                              plugin.get_parent_resource_types())

    def test_list_resources(self):
        plugin = VolumeProtectablePlugin(self._context)
        plugin._client.volumes.list = mock.MagicMock()

        plugin._client.volumes.list.return_value = [vol_info('123', [],
                                                             'name123'),
                                                    vol_info('456', [],
                                                             'name456')]
        self.assertEqual([Resource('OS::Cinder::Volume', '123', 'name123'),
                          Resource('OS::Cinder::Volume', '456', 'name456')],
                         plugin.list_resources())

    def test_show_resource(self):
        plugin = VolumeProtectablePlugin(self._context)
        plugin._client.volumes.get = mock.MagicMock()

        vol_info = namedtuple('vol_info', ['id', 'name'])
        plugin._client.volumes.get.return_value = vol_info(id='123',
                                                           name='name123')
        self.assertEqual(Resource('OS::Cinder::Volume', '123', 'name123'),
                         plugin.show_resource("123"))

    def test_get_server_dependent_resources(self):
        plugin = VolumeProtectablePlugin(self._context)
        plugin._client.volumes.list = mock.MagicMock()

        attached = [{'server_id': 'abcdef', 'name': 'name'}]
        plugin._client.volumes.list.return_value = [
            vol_info('123', attached, 'name123'),
            vol_info('456', [], 'name456'),
        ]
        self.assertEqual([Resource('OS::Cinder::Volume', '123', 'name123')],
                         plugin.get_dependent_resources(Resource(
                             "OS::Nova::Server", 'abcdef', 'name'
                         )))

    def test_get_project_dependent_resources(self):
        project = project_info('abcd', constants.PROJECT_RESOURCE_TYPE,
                               'nameabcd')
        plugin = VolumeProtectablePlugin(self._context)
        plugin._client.volumes.list = mock.MagicMock()

        volumes = [
            mock.Mock(name='Volume', id='123'),
            mock.Mock(name='Volume', id='456'),
        ]
        setattr(volumes[0], 'os-vol-tenant-attr:tenant_id', 'abcd')
        setattr(volumes[1], 'os-vol-tenant-attr:tenant_id', 'efgh')
        setattr(volumes[0], 'name', 'name123')
        setattr(volumes[1], 'name', 'name456')

        plugin._client.volumes.list.return_value = volumes
        self.assertEqual(plugin.get_dependent_resources(project),
                         [Resource('OS::Cinder::Volume', '123', 'name123')])
