
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
from karbor.services.protection.clients import glance
from karbor.tests import base


class GlanceClientTest(base.TestCase):
    def setUp(self):
        super(GlanceClientTest, self).setUp()

        self._public_url = 'http://127.0.0.1:9292'

        service_catalog = [
            {
                'endpoints': [{'publicURL': self._public_url}],
                'type': 'image',
                'name': 'glance',
            },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('glance_endpoint',
                             'http://127.0.0.1:9292',
                             'glance_client')
        gc = glance.create(self._context, cfg.CONF)
        self.assertEqual('http://127.0.0.1:9292', gc.http_client.endpoint)

    def test_create_client_by_catalog(self):
        gc = glance.create(self._context, cfg.CONF)
        self.assertEqual('http://127.0.0.1:9292', gc.http_client.endpoint)

    @mock.patch('karbor.services.protection.clients.utils.get_url')
    @mock.patch('glanceclient.client.Client')
    def test_create_client(self, create, get_url):
        get_url.return_value = self._public_url

        client_config = cfg.CONF[glance.CONFIG_GROUP]
        client_version = glance.GLANCECLIENT_VERSION
        session = object()
        args = {
            'endpoint': self._public_url,
            'token': self._context.auth_token,
            'cacert': client_config.glance_ca_cert_file,
            'insecure': client_config.glance_auth_insecure,
        }

        glance.create(self._context, cfg.CONF)
        create.assert_called_with(client_version, **args)

        glance.create(self._context, cfg.CONF, session=session)
        create.assert_called_with(client_version,
                                  endpoint=self._public_url,
                                  session=session)
