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

from karbor.common import karbor_keystone_plugin
from karbor import context
from karbor.services.operationengine import karbor_client
from karbor.tests import base


class KarborClientTest(base.TestCase):

    @mock.patch.object(karbor_keystone_plugin.KarborKeystonePlugin,
                       'get_service_endpoint')
    def test_create_client(self, get_service_endpoint):
        ctx = context.get_admin_context()
        ctx.project_id = '123'

        cfg.CONF.set_default('version', '1', 'karbor_client')

        karbor_url = "http://127.0.0.1:9090"
        sc = karbor_client.create(ctx, endpoint=karbor_url)
        self.assertEqual(karbor_url, sc.http_client.endpoint)

        karbor_url = "http://127.0.0.1:9090/$(project_id)s"
        get_service_endpoint.return_value = karbor_url
        endpoint = karbor_url.replace("$(project_id)s", ctx.project_id)
        sc = karbor_client.create(ctx)
        self.assertEqual(endpoint, sc.http_client.endpoint)
