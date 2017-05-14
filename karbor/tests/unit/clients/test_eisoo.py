#    Copyright (c) 2016 Shanghai EISOO Information Technology Corp.
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
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

import mock

from karbor.context import RequestContext
from karbor.services.protection.clients import eisoo

from karbor.tests import base


class FakeConfig(object):
    def __init__(self):
        super(FakeConfig, self).__init__()
        self.eisoo_client = EisooClient()

    def __call__(self, args):
        pass

    def register_opts(self, opts, **kwargs):
        pass


class EisooClient(object):
    def __init__(self):
        super(EisooClient, self).__init__()
        self.eisoo_endpoint = 'eisoo_endpoint'
        self.eisoo_app_id = 'eisoo_app_id'
        self.eisoo_app_secret = 'eisoo_app_secret'


class ABClientTest(base.TestCase):
    def setUp(self):
        super(ABClientTest, self).setUp()
        self._context = RequestContext(user_id='demo',
                                       project_id='asdf',
                                       auth_token='qwe',
                                       service_catalog=None)

    @mock.patch('oslo_config.cfg.ConfigOpts', FakeConfig)
    @mock.patch('karbor.utils.find_config')
    @mock.patch('os.path.abspath')
    def test_create_client_by_config_file(self, mock_findconfig, mock_abspath):
        mock_findconfig.return_value = '/etc/provider.d'
        mock_abspath.return_value = ''

        client = eisoo.create(self._context, None)
        self.assertEqual(client._app_id, 'eisoo_app_id')

    def tearDown(self):
        super(ABClientTest, self).tearDown()
