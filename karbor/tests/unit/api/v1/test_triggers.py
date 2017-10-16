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

from webob import exc

from karbor.api.v1 import triggers as trigger_api
from karbor import context
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.tests import base
from karbor.tests.unit.api import fakes


class FakeRemoteOperationApi(object):
    def create_trigger(self, context, trigger):
        if trigger.type not in ['time']:
            msg = (_("Invalid trigger type:%s") % trigger.type)
            raise exception.InvalidInput(msg)

        if trigger.properties['format'] not in ['crontab']:
            msg = (_("Invalid trigger time format type"))
            raise exception.InvalidInput(msg)

    def delete_trigger(self, context, trigger_id):
        pass

    def update_trigger(self, context, trigger):
        pass


class TriggerApiTest(base.TestCase):
    def setUp(self):
        super(TriggerApiTest, self).setUp()
        self.controller = trigger_api.TriggersController()
        self.controller.operationengine_api = FakeRemoteOperationApi()
        self.ctxt = context.RequestContext('demo', 'fakeproject',
                                           True)
        self.req = fakes.HTTPRequest.blank('/v1/triggers')
        self.default_create_trigger_param = {
            "name": "123",
            "type": "time",
            "properties": {
                "format": "crontab",
                "pattern": "* * * * *"
            },
        }

    def test_create_trigger_InvalidBody(self):
        self.assertRaises(exc.HTTPUnprocessableEntity,
                          self.controller.create,
                          self.req, {})

    def test_create_trigger_InvalidName(self):
        body = self._get_create_trigger_request_body()
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          self.req, body)

    def test_create_trigger_invalid_trigger_type(self):
        param = self.default_create_trigger_param.copy()
        param['type'] = "123"
        body = self._get_create_trigger_request_body(param)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          self.req, body)

    def test_create_trigger_invalid_trigger_formt_type(self):
        param = self.default_create_trigger_param.copy()
        param['properties']['format'] = "123"
        body = self._get_create_trigger_request_body(param)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.create,
                          self.req, body)

    def test_create_trigger(self):
        name = 'every minutes'
        param = self.default_create_trigger_param.copy()
        param['name'] = name
        body = self._get_create_trigger_request_body(param)
        trigger = self.controller.create(self.req, body)
        self.assertEqual(name, trigger['trigger_info']['name'])

    def test_delete_trigger_binded_with_operation(self):
        trigger = self._create_one_trigger()
        trigger_id = trigger['trigger_info']['id']
        self._create_scheduled_operation(trigger_id)

        self.assertRaises(exc.HTTPFailedDependency,
                          self.controller.delete,
                          self.req,
                          trigger_id)

    def test_delete_trigger(self):
        trigger = self._create_one_trigger()
        self.controller.delete(self.req, trigger['trigger_info']['id'])
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show,
                          self.req,
                          trigger['trigger_info']['id'])

    def test_update_trigger(self):
        trigger = self._create_one_trigger()

        name = 'every minutes'
        param = self.default_create_trigger_param.copy()
        param['name'] = name
        param['properties']['window'] = 10
        body = self._get_create_trigger_request_body(param)
        trigger1 = self.controller.update(
            self.req, trigger['trigger_info']['id'], body)

        self.assertEqual(name, trigger1['trigger_info']['name'])
        self.assertEqual(10, int(
            trigger1['trigger_info']['properties']['window']))

    def test_show_trigger_not_exist(self):
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.show,
                          self.req,
                          '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')

    def test_show_trigger_invalid_id(self):
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.show,
                          self.req, 1)

    def test_show_trigger(self):
        trigger = self._create_one_trigger()
        trigger1 = self.controller.show(self.req,
                                        trigger['trigger_info']['id'])
        self.assertEqual(trigger['trigger_info']['id'],
                         trigger1['trigger_info']['id'])

    def test_list_trigger(self):
        trigger = self._create_one_trigger()
        triggers = self.controller.index(self.req)
        for item in triggers['triggers']:
            if item['id'] == trigger['trigger_info']['id']:
                self.assertTrue(1)

        self.assertFalse(0)

    def _create_one_trigger(self):
        param = self.default_create_trigger_param.copy()
        body = self._get_create_trigger_request_body(param)
        return self.controller.create(self.req, body)

    def _get_create_trigger_request_body(self, param={}):
        return {"trigger_info": param}

    def _create_scheduled_operation(self, trigger_id):
        operation_info = {
            "name": "123",
            "description": "123",
            "operation_type": "protect",
            'user_id': '123',
            "project_id": "123",
            "trigger_id": trigger_id,
            "operation_definition": {
                "plan_id": ""
            },
        }
        operation = objects.ScheduledOperation(self.ctxt, **operation_info)
        operation.create()
        return operation
