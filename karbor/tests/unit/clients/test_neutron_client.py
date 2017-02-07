
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
from oslo_config import cfg

from karbor.context import RequestContext
from karbor.services.protection.clients import neutron
from karbor.tests import base


class NeutronClientTest(base.TestCase):
    def setUp(self):
        super(NeutronClientTest, self).setUp()

        self._public_url = 'http://127.0.0.1:9696'

        service_catalog = [
            {
                'endpoints': [{'publicURL': self._public_url}],
                'type': 'network',
                'name': 'neutron',
            },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('neutron_endpoint',
                             'http://127.0.0.1:9696',
                             'neutron_client')
        nc = neutron.create(self._context, cfg.CONF)
        self.assertEqual('http://127.0.0.1:9696', nc.httpclient.endpoint_url)

    def test_create_client_by_catalog(self):
        nc = neutron.create(self._context, cfg.CONF)
        self.assertEqual('http://127.0.0.1:9696', nc.httpclient.endpoint_url)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('neutronclient.client.construct_http_client')
    def test_create_client(self, create, get_url):
        get_url.return_value = self._public_url

        client_config = cfg.CONF[neutron.CONFIG_GROUP]
        session = object()
        args = {
            'endpoint_url': self._public_url,
            'token': self._context.auth_token,
            'cacert': client_config.neutron_ca_cert_file,
            'insecure': client_config.neutron_auth_insecure,
        }

        neutron.create(self._context, cfg.CONF)
        create.assert_called_with(**args)

        neutron.create(self._context, cfg.CONF, session=session)
        create.assert_called_with(endpoint_override=self._public_url,
                                  session=session)
