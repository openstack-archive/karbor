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

from keystoneauth1 import session as keystone_session
from oslo_config import cfg

from karbor.context import RequestContext
from karbor.services.protection.clients import nova
from karbor.tests import base


class NovaClientTest(base.TestCase):
    def setUp(self):
        super(NovaClientTest, self).setUp()
        service_catalog = [
            {'type': 'compute',
             'name': 'nova',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8774/v2.1/abcd'}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('nova_endpoint',
                             'http://127.0.0.1:8774/v2.1',
                             'nova_client')

        client = nova.create(self._context, cfg.CONF,
                             session=keystone_session.Session(auth=None))
        self.assertEqual('compute', client.client.service_type)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         client.client.endpoint_override)

    def test_create_client_by_catalog(self):
        client = nova.create(self._context, cfg.CONF,
                             session=keystone_session.Session(auth=None))
        self.assertEqual('compute', client.client.service_type)
        self.assertEqual('http://127.0.0.1:8774/v2.1/abcd',
                         client.client.endpoint_override)
