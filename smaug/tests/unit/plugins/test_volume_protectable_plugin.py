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
from smaug.services.protection.protectable_plugins.volume \
    import VolumeProtectablePlugin

from smaug.tests import base


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
        self.assertEqual(("OS::Nova::Server", ),
                         plugin.get_parent_resource_types())

    def test_list_resources(self):
        plugin = VolumeProtectablePlugin(self._context)
        plugin._client.volumes.list = mock.MagicMock()

        vol_info = collections.namedtuple('vol_info', ['id'])
        plugin._client.volumes.list.return_value = [vol_info('123'),
                                                    vol_info('456')]
        self.assertEqual([Resource('OS::Cinder::Volume', '123'),
                          Resource('OS::Cinder::Volume', '456')],
                         plugin.list_resources())

    def test_get_dependent_resources(self):
        plugin = VolumeProtectablePlugin(self._context)
        plugin._client.volumes.list = mock.MagicMock()

        vol_info = collections.namedtuple('vol_info', ['id', 'attachments'])
        attached = [{'server_id': 'abcdef'}]
        plugin._client.volumes.list.return_value = [vol_info('123', attached),
                                                    vol_info('456', [])]
        self.assertEqual([Resource('OS::Cinder::Volume', '123')],
                         plugin.get_dependent_resources(Resource(
                             "OS::Nova::Server", 'abcdef'
                         )))
