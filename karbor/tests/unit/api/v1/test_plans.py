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

from karbor.api.v1 import plans
from karbor.common import constants
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF

DEFAULT_NAME = 'My 3 tier application'
DEFAULT_DESCRIPTION = 'My 3 tier application protection plan'
DEFAULT_PROVIDER_ID = 'efc6a88b-9096-4bb6-8634-cda182a6e12a'
DEFAULT_PROJECT_ID = '39bb894794b741e982bd26144d2949f6'
DEFAULT_RESOURCES = [{'id': 'efc6a88b-9096-4bb6-8634-cda182a6e144',
                      "type": "OS::Cinder::Volume", "name": "name1"}]
DEFAULT_PARAMETERS = {"OS::Cinder::Volume": {"backup_name": "name"}}


class PlanApiTest(base.TestCase):
    def setUp(self):
        super(PlanApiTest, self).setUp()
        self.controller = plans.PlansController()
        self.ctxt = context.RequestContext('demo',
                                           DEFAULT_PROJECT_ID, True)

    @mock.patch(
        'karbor.services.protection.rpcapi.ProtectionAPI.show_provider')
    @mock.patch(
        'karbor.objects.plan.Plan.create')
    def test_plan_create(self, mock_plan_create, mock_provider):
        plan = self._plan_in_request_body()
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        mock_provider.return_value = fakes.PROVIDER_OS
        self.controller.create(req, body=body)
        self.assertTrue(mock_plan_create.called)

    def test_plan_create_InvalidBody(self):
        plan = self._plan_in_request_body()
        body = {"planxx": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    def test_plan_create_InvalidProviderId(self):
        plan = self._plan_in_request_body(
            name=DEFAULT_NAME,
            description=DEFAULT_DESCRIPTION,
            provider_id="",
            resources=[])
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    def test_plan_create_InvalidResources(self):
        plan = self._plan_in_request_body(
            name=DEFAULT_NAME,
            description=DEFAULT_DESCRIPTION,
            provider_id=DEFAULT_PROVIDER_ID,
            resources=[])
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(exception.InvalidInput, self.controller.create,
                          req, body=body)

    @mock.patch(
        'karbor.services.protection.rpcapi.ProtectionAPI.show_provider')
    def test_plan_create_InvalidParameters(self, mock_provider):
        parameters = {"OS::Cinder::Volume": {"test": "os"}}
        plan = self._plan_in_request_body(
            name=DEFAULT_NAME,
            description=DEFAULT_DESCRIPTION,
            provider_id=DEFAULT_PROVIDER_ID,
            parameters=parameters)
        body = {"plan": plan}
        mock_provider.return_value = fakes.PROVIDER_OS
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(exc.HTTPBadRequest, self.controller.create,
                          req, body=body)

    @mock.patch(
        'karbor.services.protection.rpcapi.ProtectionAPI.show_provider')
    def test_plan_create_InvalidProvider(self, mock_provider):
        plan = self._plan_in_request_body()
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        mock_provider.side_effect = exception.NotFound()
        self.assertRaises(exc.HTTPBadRequest, self.controller.create,
                          req, body=body)

    @mock.patch(
        'karbor.services.protection.rpcapi.ProtectionAPI.show_provider')
    def test_plan_create_InvalidProvider_and_no_parameters_specify(
            self, mock_provider):
        plan = self._plan_in_request_body(parameters={})
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        mock_provider.side_effect = exception.NotFound()
        self.assertRaises(exc.HTTPBadRequest, self.controller.create,
                          req, body=body)

    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_get')
    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_update')
    def test_plan_update(self, mock_plan_update, mock_plan_get):
        plan = self._plan_update_request_body()
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.controller.update(
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398", body=body)
        self.assertTrue(mock_plan_update.called)
        self.assertTrue(mock_plan_get.called)

    def test_plan_update_InvalidBody(self):
        plan = self._plan_update_request_body()
        body = {"planxx": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(
            exception.ValidationError, self.controller.update,
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398", body=body)
        body = {"plan": {}}
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.update,
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398", body=body)

    def test_plan_update_InvalidId(self):
        plan = self._plan_update_request_body()
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(
            exc.HTTPNotFound, self.controller.update,
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398", body=body)

    def test_plan_update_InvalidResources(self):
        plan = self._plan_update_request_body(
            name=DEFAULT_NAME,
            resources=[{'key1': 'value1'}])
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(
            exception.InvalidInput, self.controller.update,
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398", body=body)

    @mock.patch(
        'karbor.api.v1.plans.PlansController._get_all')
    def test_plan_list_detail(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

    @mock.patch(
        'karbor.api.v1.plans.PlansController._get_all')
    def test_plan_index_limit_offset(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/plans?limit=2&offset=1')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

        req = fakes.HTTPRequest.blank('/v1/plans?limit=-1&offset=1')
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

        req = fakes.HTTPRequest.blank('/v1/plans?limit=a&offset=1')
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

        url = '/v1/plans?limit=2&offset=43543564546567575'
        req = fakes.HTTPRequest.blank(url)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

    @mock.patch(
        'karbor.services.protection.rpcapi.ProtectionAPI.show_provider')
    def test_plan_create_empty_dict(self, mock_provider):
        mock_provider.return_value = fakes.PROVIDER_OS
        plan = self._plan_in_request_body(parameters={})
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.controller.create(req, body=body)

    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_get')
    def test_plan_show(self, mock_plan_get):
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.controller.show(req, '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')
        self.assertTrue(mock_plan_get.called)

    def test_plan_show_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/plans/1')
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.show,
            req, "1")

    def test_plan_show_InvalidPlanId(self):
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(
            exc.HTTPNotFound, self.controller.show,
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398")

    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_get')
    def test_plan_delete(self, mock_plan_get):
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.controller.delete(req, '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')
        self.assertTrue(mock_plan_get.called)

    def test_plan_delete_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/plans/1')
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.delete,
            req, "1")

    def test_plan_delete_InvalidPlanId(self):
        req = fakes.HTTPRequest.blank('/v1/plans')
        self.assertRaises(
            exc.HTTPNotFound, self.controller.delete,
            req, "2a9ce1f3-cc1a-4516-9435-0ebb13caa398")

    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_get')
    def test_plan_delete_authorize_failed(
            self, mock_plan_get):
        plan = self._plan_in_request_body()
        plan['project_id'] = DEFAULT_PROJECT_ID
        req = fakes.HTTPRequest.blank('/v1/plans')
        mock_plan_get.return_value = plan
        self.assertRaises(exception.PolicyNotAuthorized,
                          self.controller.delete, req,
                          "2a9ce1f3-cc1a-4516-9435-0ebb13caa398")

    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_get')
    def test_plan_update_InvalidStatus(
            self, mock_plan_get):
        plan = self._plan_update_request_body(
            name=DEFAULT_NAME,
            status=constants.PLAN_STATUS_STARTED,
            resources=DEFAULT_RESOURCES)
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        mock_plan_get.return_value = plan
        self.assertRaises(exception.InvalidPlan,
                          self.controller.update, req,
                          "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
                          body=body)

    @mock.patch(
        'karbor.api.v1.plans.PlansController._plan_get')
    def test_plan_update_InvalidInput(
            self, mock_plan_get):
        plan = self._plan_update_request_body(
            name=DEFAULT_NAME,
            status=constants.PLAN_STATUS_SUSPENDED,
            resources=DEFAULT_RESOURCES)
        body = {"plan": plan}
        req = fakes.HTTPRequest.blank('/v1/plans')
        mock_plan_get.return_value = plan
        self.assertRaises(exception.InvalidInput,
                          self.controller.update, req,
                          "2a9ce1f3-cc1a-4516-9435-0ebb13caa398",
                          body=body)

    def _plan_in_request_body(self, name=DEFAULT_NAME,
                              description=DEFAULT_DESCRIPTION,
                              provider_id=DEFAULT_PROVIDER_ID,
                              resources=DEFAULT_RESOURCES,
                              parameters=DEFAULT_PARAMETERS):
        plan_req = {
            'name': name,
            'description': description,
            'provider_id': provider_id,
            'resources': resources,
            'parameters': parameters,
        }

        return plan_req

    def _plan_update_request_body(self, name=DEFAULT_NAME,
                                  status=constants.PLAN_STATUS_STARTED,
                                  resources=DEFAULT_RESOURCES):
        plan_req = {
            'name': name,
            'resources': resources,
            'status': status,
        }

        return plan_req
