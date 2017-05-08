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
from karbor.services.protection.protectable_plugins.share \
    import ShareProtectablePlugin

from karbor.tests import base
import mock

from manilaclient.v2 import shares
from oslo_config import cfg


class ShareProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(ShareProtectablePluginTest, self).setUp()
        service_catalog = [
            {'type': 'sharev2',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8774/v2.1/abcd'}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('manila_endpoint',
                             'http://127.0.0.1:8774/v2.1',
                             'manila_client')
        plugin = ShareProtectablePlugin(self._context)

        self.assertEqual(
            'http://127.0.0.1:8774/v2.1/abcd',
            plugin._client(self._context).client.endpoint_url)

    def test_create_client_by_catalog(self):
        plugin = ShareProtectablePlugin(self._context)

        self.assertEqual(
            'http://127.0.0.1:8774/v2.1/abcd',
            plugin._client(self._context).client.endpoint_url)

    def test_get_resource_type(self):
        plugin = ShareProtectablePlugin(self._context)

        self.assertEqual("OS::Manila::Share", plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = ShareProtectablePlugin(self._context)
        self.assertEqual(("OS::Keystone::Project", ),
                         plugin.get_parent_resource_types())

    @mock.patch.object(shares.ShareManager, 'list')
    def test_list_resources(self, mock_share_list):
        plugin = ShareProtectablePlugin(self._context)

        share_info = collections.namedtuple('share_info', ['id', 'name',
                                                           'status'])
        mock_share_list.return_value = [
            share_info(id='123', name='name123', status='available'),
            share_info(id='456', name='name456', status='available')]
        self.assertEqual([Resource('OS::Manila::Share', '123', 'name123'),
                          Resource('OS::Manila::Share', '456', 'name456')],
                         plugin.list_resources(self._context))

    @mock.patch.object(shares.ShareManager, 'get')
    def test_show_resource(self, mock_share_get):
        plugin = ShareProtectablePlugin(self._context)

        share_info = collections.namedtuple('share_info', ['id', 'name',
                                                           'status'])
        mock_share_get.return_value = share_info(id='123', name='name123',
                                                 status='available')
        self.assertEqual(Resource('OS::Manila::Share', '123', 'name123'),
                         plugin.show_resource(self._context, '123'))

    @mock.patch.object(shares.ShareManager, 'list')
    def test_get_dependent_resources(self, mock_share_list):
        plugin = ShareProtectablePlugin(self._context)

        share_info = collections.namedtuple(
            'share_info', ['id', 'name', 'status', 'project_id'])
        project_info = collections.namedtuple(
            'share_info', ['id', 'name', 'status'])
        mock_share_list.return_value = [
            share_info(id='123', name='name123', status='available',
                       project_id='abcd'),
            share_info(id='456', name='name456', status='available',
                       project_id='abcd')]
        project = project_info(id='abcd', name='name456', status='available')
        self.assertEqual([Resource('OS::Manila::Share', '123', 'name123'),
                          Resource('OS::Manila::Share', '456', 'name456')],
                         plugin.get_dependent_resources(
                             self._context, project))
