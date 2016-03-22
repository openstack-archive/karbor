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
from smaug import resource
from smaug.services.protection.protectable_plugins.image import \
    ImageProtectablePlugin
from smaug.tests import base

CONF = cfg.CONF


class ImageProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(ImageProtectablePluginTest, self).setUp()
        service_catalog = [{
            'type': 'image',
            'endpoints': [{'publicURL': 'http://127.0.0.1:9292'}]
        }, {
            'type': 'compute',
            'endpoints': [{'publicURL': 'http://127.0.0.1:8774/v2.1/abcd'}]
        }]
        self._context = RequestContext(user_id='admin',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        CONF.set_default('glance_endpoint', 'http://127.0.0.1:9292',
                         'glance_client')
        CONF.set_default('nova_endpoint', 'http://127.0.0.1:8774/v2.1',
                         'nova_client')
        plugin = ImageProtectablePlugin(self._context)
        self.assertEqual(plugin._glance_client.http_client.endpoint,
                         'http://127.0.0.1:9292')
        self.assertEqual(plugin._nova_client.client.management_url,
                         'http://127.0.0.1:8774/v2.1/abcd')

    def test_create_client_by_catalog(self):
        CONF.set_default('glance_catalog_info', 'image:glance:publicURL',
                         'glance_client')
        CONF.set_default('nova_catalog_info', 'compute:nova:publicURL',
                         'nova_client')
        plugin = ImageProtectablePlugin(self._context)
        self.assertEqual(plugin._glance_client.http_client.endpoint,
                         'http://127.0.0.1:9292')
        self.assertEqual(plugin._nova_client.client.management_url,
                         'http://127.0.0.1:8774/v2.1/abcd')

    def test_get_resource_type(self):
        plugin = ImageProtectablePlugin(self._context)
        self.assertEqual(plugin.get_resource_type(),
                         constants.IMAGE_RESOURCE_TYPE)

    def test_get_parent_resource_type(self):
        plugin = ImageProtectablePlugin(self._context)
        self.assertEqual(plugin.get_parent_resource_types(),
                         (constants.SERVER_RESOURCE_TYPE, ))

    def test_list_resources(self):
        image_info = namedtuple('image_info', field_names=['id'])
        plugin = ImageProtectablePlugin(self._context)
        plugin._glance_client.images.list = mock.MagicMock(return_value=[
            image_info('123'),
            image_info('456'),
        ])
        self.assertEqual(plugin.list_resources(),
                         [resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                            id='123'),
                          resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                            id='456')
                          ])

    def test_get_dependent_resources(self):
        server_info = namedtuple('server_info',
                                 field_names=['id', 'type', 'image'])
        vm = server_info(id='789',
                         type=constants.SERVER_RESOURCE_TYPE,
                         image=dict(id='123'))
        plugin = ImageProtectablePlugin(self._context)
        plugin._nova_client.servers.get = mock.MagicMock(return_value=vm)
        self.assertEqual(plugin.get_dependent_resources(vm),
                         [resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                            id='123')])
