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

import mock
from oslo_config import cfg

from karbor.common import karbor_keystone_plugin as kkp
from karbor.context import RequestContext
from karbor import exception
from karbor.services.protection.clients import utils
from karbor.tests import base


class ClientUtilsTest(base.TestCase):
    def setUp(self):
        super(ClientUtilsTest, self).setUp()

        self._service = ''
        self._public_url = 'http://127.0.0.1:8776/v3/abcd'

        service_catalog = [
            {'type': 'volumev3',
             'name': 'cinderv3',
             'endpoints': [{'publicURL': self._public_url}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    @mock.patch.object(cfg.ConfigOpts, '_get')
    def test_get_url_by_endpoint(self, get_opt):
        endpoint = 'http://127.0.0.1:8776/v3'
        get_opt.return_value = endpoint

        self.assertEqual(
            endpoint, utils.get_url(self._service, self._context, cfg.CONF))

        self.assertEqual(
            endpoint + '/%s' % self._context.project_id,
            utils.get_url(self._service, self._context, cfg.CONF,
                          '%(url)s/%(project)s'))

    @mock.patch.object(cfg.ConfigOpts, '_get')
    def test_get_url_by_catalog(self, get_opt):
        def _get_opt(name):
            if name.find('catalog_info') >= 0:
                return 'volumev3:cinderv3:publicURL'
            return None
        get_opt.side_effect = _get_opt

        self.assertEqual(
            self._public_url,
            utils.get_url(self._service, self._context, cfg.CONF))

    @mock.patch.object(kkp.KarborKeystonePlugin, 'get_service_endpoint')
    def test_get_url_by_keystone_plugin(self, get_endpoint):
        endpoint = "http://127.0.0.1:8776"
        keystone_plugin = kkp.KarborKeystonePlugin()
        get_endpoint.return_value = endpoint

        config = mock.Mock()
        config.test_service_endpoint = None
        config.test_service_catalog_info = None
        self.assertEqual(
            endpoint,
            utils.get_url('test_service', self._context, config,
                          keystone_plugin=keystone_plugin))

    @mock.patch.object(cfg.ConfigOpts, '_get')
    def test_get_url_except(self, get_opt):
        get_opt.return_value = None
        self.assertRaisesRegex(exception.KarborException,
                               "Couldn't find the endpoint of service.*",
                               utils.get_url, self._service,
                               self._context, cfg.CONF)
