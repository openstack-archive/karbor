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
from karbor.services.protection.clients import manila
from karbor.tests import base


class ManilaClientTest(base.TestCase):
    def setUp(self):
        super(ManilaClientTest, self).setUp()

        self._public_url = 'http://127.0.0.1:8776/v2/abcd'

        service_catalog = [
            {'type': 'sharev2',
             'name': 'manilav2',
             'endpoints': [{'publicURL': self._public_url}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('manilaclient.client.Client')
    def test_create_client(self, create, get_url):
        get_url.return_value = self._public_url

        client_version = manila.MANILACLIENT_VERSION

        session = keystone_session.Session(auth=None)
        manila.create(self._context, cfg.CONF, session=session)
        create.assert_called_with(client_version,
                                  endpoint_override=self._public_url,
                                  session=session)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('manilaclient.client.Client')
    def test_create_client_without_session(self, create, get_url):
        get_url.return_value = self._public_url

        client_config = cfg.CONF[manila.CONFIG_GROUP]
        client_version = manila.MANILACLIENT_VERSION
        args = {
            'input_auth_token': self._context.auth_token,
            'project_id': self._context.project_id,
            'service_catalog_url': self._public_url,
            'cacert': client_config.manila_ca_cert_file,
            'insecure': client_config.manila_auth_insecure,
        }

        manila.create(self._context, cfg.CONF)
        create.assert_called_with(client_version, **args)
