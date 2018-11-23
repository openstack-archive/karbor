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
from mock import mock

from karbor.api.v1 import copies
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes
from webob import exc

PROVIDER_ID_1 = 'efc6a88b-9096-4bb6-8634-cda182a6e12a'
PROVIDER_ID_2 = '3241a88b-9096-4bb6-8634-cda182a6e12a'
DEFAULT_PROJECT_ID = '39bb894794b741e982bd26144d2949f6'
DEFAULT_PLAN_ID = '603b894794b741e982bd26144d2949f6'


class FakePlan(object):
    def __init__(self, values):
        self.id = values.get('id')
        self.provider_id = values.get('provider_id')
        self.parameters = values.get('parameters')


class CopiesApiTest(base.TestCase):

    def setUp(self):
        super(CopiesApiTest, self).setUp()
        self.controller = copies.CopiesController()
        self.ctxt = context.RequestContext('demo',
                                           DEFAULT_PROJECT_ID, True)

    @mock.patch('karbor.objects.Plan.get_by_id')
    @mock.patch('karbor.services.protection.api.API.list_checkpoints')
    @mock.patch('karbor.services.protection.api.API.copy')
    def test_copies_create(self, mock_copy,
                           mock_list_checkpoints, mock_plan_get):
        mock_plan_get.return_value = FakePlan(
            {'id': DEFAULT_PLAN_ID,
             'provider_id': PROVIDER_ID_1,
             'parameters': {}})
        mock_list_checkpoints.return_value = ['fake_checkpoint_id']
        copy = self._copy_in_request_body(DEFAULT_PLAN_ID, {})
        body = {"copy": copy}
        req = fakes.HTTPRequest.blank('/v1/copies')
        self.controller.create(req, PROVIDER_ID_1, body=body)
        self.assertEqual(True, mock_copy.called)

    def test_copies_create_with_invalid_provider_id(self):
        copy = self._copy_in_request_body(DEFAULT_PLAN_ID, {})
        body = {"copy": copy}
        req = fakes.HTTPRequest.blank('/v1/copies')
        self.assertRaises(exception.InvalidInput, self.controller.create, req,
                          'fake_invalid_provider_id', body=body)

    @mock.patch('karbor.objects.Plan.get_by_id')
    def test_copies_create_with_invalid_plan(self, mock_plan_get):
        mock_plan_get.side_effect = exception.PlanNotFound
        copy = self._copy_in_request_body(DEFAULT_PLAN_ID, {})
        body = {"copy": copy}
        req = fakes.HTTPRequest.blank('/v1/copies')
        self.assertRaises(exc.HTTPNotFound, self.controller.create, req,
                          PROVIDER_ID_1, body=body)

    @mock.patch('karbor.objects.Plan.get_by_id')
    def test_copies_create_with_different_provider_id(self, mock_plan_get):
        mock_plan_get.return_value = FakePlan(
            {'id': DEFAULT_PLAN_ID,
             'provider_id': PROVIDER_ID_2,
             'parameters': {}})
        copy = self._copy_in_request_body(DEFAULT_PLAN_ID, {})
        body = {"copy": copy}
        req = fakes.HTTPRequest.blank('/v1/copies')
        self.assertRaises(exception.InvalidInput, self.controller.create, req,
                          PROVIDER_ID_1, body=body)

    @mock.patch('karbor.objects.Plan.get_by_id')
    @mock.patch('karbor.services.protection.api.API.list_checkpoints')
    def test_copies_create_with_no_checkpoints_exist(
            self, mock_list_checkpoints, mock_plan_get):
        mock_plan_get.return_value = FakePlan(
            {'id': DEFAULT_PLAN_ID,
             'provider_id': PROVIDER_ID_1,
             'parameters': {}})
        mock_list_checkpoints.return_value = []
        copy = self._copy_in_request_body(DEFAULT_PLAN_ID, {})
        body = {"copy": copy}
        req = fakes.HTTPRequest.blank('/v1/copies')
        self.assertRaises(exception.InvalidInput, self.controller.create, req,
                          PROVIDER_ID_1, body=body)

    @mock.patch('karbor.objects.Plan.get_by_id')
    @mock.patch('karbor.services.protection.api.API.list_checkpoints')
    @mock.patch('karbor.services.protection.api.API.copy')
    def test_copies_create_with_protection_copy_failed(
            self, mock_copy, mock_list_checkpoints, mock_plan_get):
        mock_plan_get.return_value = FakePlan(
            {'id': DEFAULT_PLAN_ID,
             'provider_id': PROVIDER_ID_1,
             'parameters': {}})
        mock_list_checkpoints.return_value = ['fake_checkpoint_id']
        mock_copy.side_effect = exception.FlowError
        copy = self._copy_in_request_body(DEFAULT_PLAN_ID, {})
        body = {"copy": copy}
        req = fakes.HTTPRequest.blank('/v1/copies')
        self.assertRaises(exception.FlowError, self.controller.create,
                          req, PROVIDER_ID_1, body=body)

    def _copy_in_request_body(self, plan_id, parameters):
        return {
            'plan_id': plan_id,
            'parameters': parameters
        }
