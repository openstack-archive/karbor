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
from oslo_utils import uuidutils
from webob import exc

from karbor.api.v1 import plans as plan_api
from karbor.api.v1 import scheduled_operations as operation_api
from karbor.api.v1 import triggers as trigger_api
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes
from karbor.tests.unit.api.v1 import test_triggers


class FakeRemoteOperationApi(object):
    def __init__(self):
        super(FakeRemoteOperationApi, self).__init__()
        self._create_operation_exception = None
        self._delete_operation_exception = None

    def create_scheduled_operation(self, context, operation):
        if self._create_operation_exception:
            raise self._create_operation_exception

    def delete_scheduled_operation(self, context, operation_id, trigger_id):
        if self._delete_operation_exception:
            raise self._delete_operation_exception


class ScheduledOperationApiTest(base.TestCase):

    def setUp(self):
        super(ScheduledOperationApiTest, self).setUp()

        self.remote_operation_api = FakeRemoteOperationApi()
        self.controller = operation_api.ScheduledOperationController()
        self.controller.operationengine_api = self.remote_operation_api

        self.ctxt = context.RequestContext('demo', 'fakeproject', True)
        self.req = fakes.HTTPRequest.blank('/v1/scheduled_operations')

        trigger = self._create_trigger()
        self._plan = self._create_plan(uuidutils.generate_uuid())
        self.default_create_operation_param = {
            "name": "123",
            "description": "123",
            "operation_type": "protect",
            "trigger_id": trigger['trigger_info']['id'],
            "operation_definition": {
                "plan_id": self._plan['id'],
                "provider_id": self._plan['provider_id']
            },
        }

    def test_create_operation_InvalidBody(self):
        self.assertRaises(exc.HTTPUnprocessableEntity,
                          self.controller.create,
                          self.req, {})

    def test_create_operation_InvalidName(self):
        body = self._get_create_operation_request_body()
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          self.req, body)

    def test_create_operation_invalid_trigger(self):
        param = self.default_create_operation_param.copy()
        param['trigger_id'] = 123
        body = self._get_create_operation_request_body(param)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          self.req, body)

    def test_create_operation_receive_invalid_except(self):
        self.remote_operation_api._create_operation_exception =\
            exception.TriggerIsInvalid(trigger_id=None)

        param = self.default_create_operation_param.copy()
        body = self._get_create_operation_request_body(param)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          self.req, body)

        self.remote_operation_api._create_operation_exception = None

    def test_create_operation_receive_unknown_except(self):
        self.remote_operation_api._create_operation_exception =\
            exception.TriggerNotFound(id=None)

        param = self.default_create_operation_param.copy()
        body = self._get_create_operation_request_body(param)
        self.assertRaises(exc.HTTPInternalServerError,
                          self.controller.create,
                          self.req, body)

        self.remote_operation_api._create_operation_exception = None

    def test_create_operation(self):
        name = 'my protect'
        param = self.default_create_operation_param.copy()
        param['name'] = name
        body = self._get_create_operation_request_body(param)
        operation = self.controller.create(self.req, body)
        self.assertEqual(name, operation['scheduled_operation']['name'])

    def test_delete_operation_receive_NotFound_except(self):
        self.remote_operation_api._delete_operation_exception =\
            exception.ScheduledOperationStateNotFound(op_id=None)

        operation = self._create_one_operation()
        self.assertRaises(exc.HTTPInternalServerError,
                          self.controller.delete,
                          self.req,
                          operation['scheduled_operation']['id'])

        self.remote_operation_api._delete_operation_exception = None

    def test_delete_operation(self):
        operation = self._create_one_operation()
        self.controller.delete(self.req,
                               operation['scheduled_operation']['id'])
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show,
                          self.req,
                          operation['scheduled_operation']['id'])

    def test_show_operation_not_exist(self):
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show,
                          self.req,
                          '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')

    def test_show_operation_invalid_id(self):
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.show,
                          self.req, 1)

    def test_show_operation(self):
        operation = self._create_one_operation()
        operation1 = self.controller.show(
            self.req, operation['scheduled_operation']['id'])
        self.assertEqual(operation['scheduled_operation']['id'],
                         operation1['scheduled_operation']['id'])

    def test_list_operation(self):
        operation = self._create_one_operation()
        operations = self.controller.index(self.req)
        for item in operations['operations']:
            if item['id'] == operation['scheduled_operation']['id']:
                self.assertTrue(1)

        self.assertFalse(0)

    def _create_one_operation(self):
        param = self.default_create_operation_param.copy()
        body = self._get_create_operation_request_body(param)
        return self.controller.create(self.req, body)

    def _get_create_operation_request_body(self, param={}):
        return {"scheduled_operation": param}

    def _create_trigger(self):
        create_trigger_param = {
            "trigger_info": {
                "name": "123",
                "type": "time",
                "properties": {
                    "format": "crontab",
                    "pattern": "* * * * *"
                },
            }
        }
        controller = trigger_api.TriggersController()
        controller.operationengine_api = test_triggers.FakeRemoteOperationApi()
        req = fakes.HTTPRequest.blank('/v1/triggers')
        return controller.create(req, create_trigger_param)

    @mock.patch(
        'karbor.services.protection.rpcapi.ProtectionAPI.show_provider')
    def _create_plan(self, provider_id, mock_provider):
        create_plan_param = {
            'plan': {
                'name': '123',
                'provider_id': provider_id,
                'resources': [
                    {'id': '39bb894794b741e982bd26144d2949f6',
                     'type': 'OS::Cinder::Volume', 'name': '123'}
                ],
                'parameters': {"OS::Cinder::Volume": {"backup_name": "test"}},
            }
        }
        controller = plan_api.PlansController()
        mock_provider.return_value = fakes.PROVIDER_OS
        req = fakes.HTTPRequest.blank('/v1/plans')
        plan = controller.create(req, create_plan_param)
        return plan['plan']
