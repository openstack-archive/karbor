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

from webob import exc

from smaug.api.v1 import providers
from smaug import context
from smaug.tests import base
from smaug.tests.unit.api import fakes

CONF = cfg.CONF


class ProvidersApiTest(base.TestCase):
    def setUp(self):
        super(ProvidersApiTest, self).setUp()
        self.controller = providers.ProvidersController()
        self.ctxt = context.RequestContext('admin', 'fakeproject', True)

    @mock.patch(
        'smaug.api.v1.providers.ProvidersController._get_all')
    def test_providers_list_detail(self, moak_get_all):
        req = fakes.HTTPRequest.blank('/v1/providers')
        self.controller.index(req)
        self.assertTrue(moak_get_all.called)

    @mock.patch(
        'smaug.services.protection.api.API.show_provider')
    def test_providers_show(self, moak_show_provider):
        req = fakes.HTTPRequest.blank('/v1/providers')
        self.controller.\
            show(req, '2220f8b1-975d-4621-a872-fa9afb43cb6c')
        self.assertTrue(moak_show_provider.called)

    def test_providers_show_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/providers')
        self.assertRaises(exc.HTTPBadRequest, self.controller.show,
                          req, "1")
