# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from collections import namedtuple
from glanceclient.v2 import images
from karbor.common import constants
from karbor.context import RequestContext
from karbor import resource
from karbor.services.protection.protectable_plugins.image import \
    ImageProtectablePlugin
from karbor.tests import base
from keystoneauth1 import session as keystone_session
import mock
from novaclient.v2 import servers
from oslo_config import cfg

CONF = cfg.CONF

image_info = namedtuple('image_info', field_names=['id', 'owner', 'name',
                                                   'status'])
server_info = namedtuple('server_info', field_names=['id', 'type', 'name',
                                                     'image'])
project_info = namedtuple('project_info', field_names=['id', 'type', 'name'])


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
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_create_client_by_endpoint(self, mock_generate_session):
        CONF.set_default('glance_endpoint', 'http://127.0.0.1:9292',
                         'glance_client')
        CONF.set_default('nova_endpoint', 'http://127.0.0.1:8774/v2.1',
                         'nova_client')
        plugin = ImageProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual(
            plugin._glance_client(self._context).http_client.endpoint_override,
            'http://127.0.0.1:9292')
        self.assertEqual(
            plugin._nova_client(self._context).client.endpoint_override,
            'http://127.0.0.1:8774/v2.1/abcd')

    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_create_client_by_catalog(self, mock_generate_session):
        CONF.set_default('glance_catalog_info', 'image:glance:publicURL',
                         'glance_client')
        CONF.set_default('nova_catalog_info', 'compute:nova:publicURL',
                         'nova_client')
        plugin = ImageProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        self.assertEqual(
            plugin._glance_client(self._context).http_client.endpoint_override,
            'http://127.0.0.1:9292')
        self.assertEqual(
            plugin._nova_client(self._context).client.endpoint_override,
            'http://127.0.0.1:8774/v2.1/abcd')

    def test_get_resource_type(self):
        plugin = ImageProtectablePlugin(self._context)
        self.assertEqual(
            plugin.get_resource_type(),
            constants.IMAGE_RESOURCE_TYPE)

    def test_get_parent_resource_type(self):
        plugin = ImageProtectablePlugin(self._context)
        self.assertItemsEqual(
            plugin.get_parent_resource_types(),
            (constants.SERVER_RESOURCE_TYPE, constants.PROJECT_RESOURCE_TYPE))

    @mock.patch.object(images.Controller, 'list')
    def test_list_resources(self, mokc_image_list):
        plugin = ImageProtectablePlugin(self._context)
        mokc_image_list.return_value = [
            image_info(id='123', name='name123', owner='abcd',
                       status='active'),
            image_info(id='456', name='name456', owner='efgh',
                       status='active'),
        ]
        self.assertEqual(plugin.list_resources(self._context),
                         [resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                            id='123', name='name123'),
                          resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                            id='456', name='name456')
                          ])

    @mock.patch.object(images.Controller, 'get')
    def test_show_resource(self, mock_image_get):
        image_info = namedtuple('image_info', field_names=['id', 'name',
                                                           'status'])
        plugin = ImageProtectablePlugin(self._context)
        mock_image_get.return_value = image_info(id='123', name='name123',
                                                 status='active')
        self.assertEqual(plugin.show_resource(self._context, '123'),
                         resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                           id='123', name='name123'))

    @mock.patch.object(images.Controller, 'get')
    @mock.patch.object(servers.ServerManager, 'get')
    @mock.patch('karbor.services.protection.client_factory.ClientFactory.'
                '_generate_session')
    def test_get_server_dependent_resources(self, mock_generate_session,
                                            mock_server_get,
                                            mock_image_get):
        vm = server_info(id='server1',
                         type=constants.SERVER_RESOURCE_TYPE,
                         name='nameserver1',
                         image=dict(id='123', name='name123'))
        image = image_info(id='123', name='name123', owner='abcd',
                           status='active')
        plugin = ImageProtectablePlugin(self._context)
        mock_generate_session.return_value = keystone_session.Session(
            auth=None)
        mock_server_get.return_value = vm
        mock_image_get.return_value = image
        self.assertEqual(plugin.get_dependent_resources(self._context, vm),
                         [resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                                            id='123', name='name123')])

    @mock.patch.object(images.Controller, 'list')
    def test_get_project_dependent_resources(self, mock_image_list):
        project = project_info(id='abcd', type=constants.PROJECT_RESOURCE_TYPE,
                               name='nameabcd')
        plugin = ImageProtectablePlugin(self._context)
        mock_image_list.return_value = [
            image_info('123', 'abcd', 'nameabcd', 'active'),
            image_info('456', 'efgh', 'nameefgh', 'active'),
        ]
        self.assertEqual(
            plugin.get_dependent_resources(self._context, project),
            [resource.Resource(type=constants.IMAGE_RESOURCE_TYPE,
                               name='nameabcd',
                               id='123')])
