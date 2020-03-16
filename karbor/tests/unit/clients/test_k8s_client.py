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

from oslo_config import cfg

from karbor.context import RequestContext
from karbor.services.protection.clients import k8s
from karbor.tests import base


class KubernetesClientTest(base.TestCase):
    def setUp(self):
        super(KubernetesClientTest, self).setUp()
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=None)

        self.conf = cfg.ConfigOpts()
        k8s.register_opts(self.conf)
        self.host_url = 'https://192.168.98.35:6443'
        self.conf.set_default('k8s_host',
                              self.host_url,
                              'k8s_client')
        self.conf.set_override('k8s_ssl_ca_cert',
                               '/etc/provider.d/server-ca.crt',
                               'k8s_client')
        self.conf.set_override('k8s_cert_file',
                               '/etc/provider.d/client-admin.crt',
                               'k8s_client')
        self.conf.set_override('k8s_key_file',
                               '/etc/provider.d/client-admin.key',
                               'k8s_client')

    def test_create_client(self):

        client = k8s.create(self._context, self.conf)
        self.assertEqual(client.api_client.configuration.host, self.host_url)
