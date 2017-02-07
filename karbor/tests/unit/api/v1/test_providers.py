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

from karbor.api.v1 import providers
from karbor import context
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF


class ProvidersApiTest(base.TestCase):
    def setUp(self):
        super(ProvidersApiTest, self).setUp()
        self.controller = providers.ProvidersController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.api.v1.providers.ProvidersController._get_all')
    def test_providers_list_detail(self, moak_get_all):
        req = fakes.HTTPRequest.blank('/v1/providers')
        self.controller.index(req)
        self.assertTrue(moak_get_all.called)

    @mock.patch(
        'karbor.services.protection.api.API.show_provider')
    def test_providers_show(self, moak_show_provider):
        req = fakes.HTTPRequest.blank('/v1/providers')
        self.controller.show(req, '2220f8b1-975d-4621-a872-fa9afb43cb6c')
        self.assertTrue(moak_show_provider.called)

    def test_providers_show_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/providers')
        self.assertRaises(exc.HTTPBadRequest, self.controller.show,
                          req, "1")

    @mock.patch(
        'karbor.services.protection.api.API.'
        'show_checkpoint')
    def test_checkpoint_show(self, moak_show_checkpoint):
        req = fakes.HTTPRequest.blank('/v1/providers/'
                                      '{provider_id}/checkpoints/')
        moak_show_checkpoint.return_value = {
            "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a",
            "project_id": "446a04d8-6ff5-4e0e-99a4-827a6389e9ff",
            "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c"
        }
        self.controller.checkpoints_show(
            req,
            '2220f8b1-975d-4621-a872-fa9afb43cb6c',
            '2220f8b1-975d-4621-a872-fa9afb43cb6c'
        )
        self.assertTrue(moak_show_checkpoint.called)

    @mock.patch(
        'karbor.services.protection.api.API.'
        'show_checkpoint')
    def test_checkpoint_show_Invalid(self, moak_show_checkpoint):
        req = fakes.HTTPRequest.blank('/v1/providers/'
                                      '{provider_id}/checkpoints/')
        moak_show_checkpoint.return_value = {
            "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a",
            "project_id": "446a04d8-6ff5-4e0e-99a4-827a6389e9ff",
            "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c"
        }
        self.assertRaises(exc.HTTPBadRequest, self.controller.checkpoints_show,
                          req, '2220f8b1-975d-4621-a872-fa9afb43cb6c',
                          '1')

    @mock.patch(
        'karbor.services.protection.api.API.'
        'list_checkpoints')
    def test_checkpoint_index(self, moak_list_checkpoints):
        req = fakes.HTTPRequest.blank('/v1/providers/'
                                      '{provider_id}/checkpoints/')
        moak_list_checkpoints.return_value = [
            {
                "provider_id": "efc6a88b-9096-4bb6-8634-cda182a6e12a",
                "project_id": "446a04d8-6ff5-4e0e-99a4-827a6389e9ff",
                "id": "2220f8b1-975d-4621-a872-fa9afb43cb6c"
            }
        ]
        self.controller.checkpoints_index(
            req,
            '2220f8b1-975d-4621-a872-fa9afb43cb6c')
        self.assertTrue(moak_list_checkpoints.called)

    @mock.patch(
        'karbor.services.protection.api.API.'
        'delete')
    def test_checkpoints_delete(self, moak_delete):
        req = fakes.HTTPRequest.blank('/v1/providers/'
                                      '{provider_id}/checkpoints/')
        self.controller.checkpoints_delete(
            req,
            '2220f8b1-975d-4621-a872-fa9afb43cb6c',
            '2220f8b1-975d-4621-a872-fa9afb43cb6c')
        self.assertTrue(moak_delete.called)

    @mock.patch(
        'karbor.services.protection.api.API.'
        'protect')
    @mock.patch(
        'karbor.objects.plan.Plan.get_by_id')
    def test_checkpoints_create(self, mock_plan_create,
                                mock_protect):
        checkpoint = {
            "plan_id": "2c3a12ee-5ea6-406a-8b64-862711ff85e6"
        }
        body = {"checkpoint": checkpoint}
        req = fakes.HTTPRequest.blank('/v1/providers/'
                                      '{provider_id}/checkpoints/')
        mock_plan_create.return_value = {
            "plan_id": "2c3a12ee-5ea6-406a-8b64-862711ff85e6",
            "provider_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c"
        }
        mock_protect.return_value = {
            "checkpoint_id": "2c3a12ee-5ea6-406a-8b64-862711ff85e6"
        }
        self.controller.checkpoints_create(
            req,
            '2220f8b1-975d-4621-a872-fa9afb43cb6c',
            body)
        self.assertTrue(mock_plan_create.called)
        self.assertTrue(mock_protect.called)
