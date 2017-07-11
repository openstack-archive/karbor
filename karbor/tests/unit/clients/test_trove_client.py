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
from karbor.services.protection.clients import trove
from karbor.tests import base


class TroveClientTest(base.TestCase):
    def setUp(self):
        super(TroveClientTest, self).setUp()

        self._public_url = 'http://127.0.0.1:8776/v2/abcd'

        service_catalog = [
            {'type': 'database',
             'name': 'trove',
             'endpoints': [{'publicURL': self._public_url}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('troveclient.client.Client')
    def test_create_client(self, create, get_url):
        get_url.return_value = self._public_url

        client_version = trove.TROVECLIENT_VERSION

        session = keystone_session.Session(auth=None)
        trove.create(self._context, cfg.CONF, session=session)
        create.assert_called_with(client_version,
                                  endpoint_override=self._public_url,
                                  session=session)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('troveclient.client.Client')
    def test_create_client_without_session(self, create, get_url):
        get_url.return_value = self._public_url

        client_config = cfg.CONF[trove.CONFIG_GROUP]
        client_version = trove.TROVECLIENT_VERSION
        args = {
            'input_auth_token': self._context.auth_token,
            'project_id': self._context.project_id,
            'service_catalog_url': self._public_url,
            'cacert': client_config.trove_ca_cert_file,
            'insecure': client_config.trove_auth_insecure,
        }

        trove.create(self._context, cfg.CONF)
        create.assert_called_with(client_version, **args)
