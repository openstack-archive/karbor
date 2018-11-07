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

from keystoneauth1 import session as keystone_session
from oslo_config import cfg

from karbor.context import RequestContext
from karbor.services.protection.clients import freezer
from karbor.tests import base


class FreezerClientTest(base.TestCase):
    def setUp(self):
        super(FreezerClientTest, self).setUp()
        self._public_url = 'http://127.0.0.1:9090'
        self._auth_url = 'http://127.0.0.1/v2.0'
        service_catalog = [
            {'type': 'backup',
             'name': 'freezer',
             'endpoints': [{'publicURL': self._public_url}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       project_name='efgh',
                                       auth_token='ijkl',
                                       service_catalog=service_catalog)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('freezerclient.v1.client.Client')
    def test_create_client(self, create, get_url):
        get_url.return_value = self._public_url

        session = keystone_session.Session(auth=None)
        freezer.create(self._context, cfg.CONF, session=session)
        create.assert_called_with(endpoint=self._public_url,
                                  session=session)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('freezerclient.v1.client.Client')
    def test_create_client_without_session(self, create, get_url):
        get_url.return_value = self._public_url

        client_config = cfg.CONF[freezer.CONFIG_GROUP]
        # due to freezer client bug, auth_uri should be specified
        cfg.CONF.set_default('auth_uri',
                             self._auth_url,
                             freezer.CONFIG_GROUP)
        args = {
            'project_id': self._context.project_id,
            'project_name': self._context.project_name,
            'cacert': client_config.freezer_ca_cert_file,
            'insecure': client_config.freezer_auth_insecure,
            'endpoint': self._public_url,
            'token': self._context.auth_token,
            'auth_url': self._auth_url,
        }

        freezer.create(self._context, cfg.CONF)
        create.assert_called_with(**args)
