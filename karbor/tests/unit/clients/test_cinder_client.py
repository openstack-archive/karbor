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

from karbor.context import RequestContext
from karbor.services.protection.clients import cinder
from karbor.tests import base


class CinderClientTest(base.TestCase):
    def setUp(self):
        super(CinderClientTest, self).setUp()

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

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('cinder_endpoint',
                             'http://127.0.0.1:8776/v3',
                             'cinder_client')
        client = cinder.create(self._context, cfg.CONF)
        self.assertEqual('volumev3', client.client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v3/abcd',
                         client.client.management_url)

    def test_create_client_by_catalog(self):
        client = cinder.create(self._context, cfg.CONF)
        self.assertEqual('volumev3', client.client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v3/abcd',
                         client.client.management_url)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('cinderclient.client.Client')
    def test_create_client(self, create, get_url):
        get_url.return_value = self._public_url

        client_config = cfg.CONF[cinder.CONFIG_GROUP]
        client_version = cinder.CINDERCLIENT_VERSION
        session = object()
        args = {
            'project_id': self._context.project_id,
            'cacert': client_config.cinder_ca_cert_file,
            'insecure': client_config.cinder_auth_insecure,
        }

        cinder.create(self._context, cfg.CONF)
        create.assert_called_with(client_version, **args)

        cinder.create(self._context, cfg.CONF, session=session)
        create.assert_called_with(client_version,
                                  endpoint_override=self._public_url,
                                  session=session)
