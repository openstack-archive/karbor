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

from oslo_messaging.rpc import dispatcher as rpc_dispatcher

from smaug import context
from smaug import objects
from smaug.operationengine import manager as service_manager
from smaug.operationengine import scheduled_operation_state
from smaug.tests import base


class FakeTriggerManager(object):

    def __init__(self):
        self._trigger = {}

    def register_operation(self, trigger_id, operation_id, **kwargs):
        if trigger_id in self._trigger:
            self._trigger[trigger_id].append(operation_id)

    def unregister_operation(self, trigger_id, operation_id, **kwargs):
        pass

    def add_trigger(self, trigger_id, trigger_type, trigger_property):
        self._trigger[trigger_id] = []


class OperationEngineManagerTestCase(base.TestCase):
    """Test cases for OperationEngineManager class."""

    def setUp(self):
        super(OperationEngineManagerTestCase, self).setUp()

        self.manager = service_manager.OperationEngineManager()
        self.manager._service_id = 0
        self.manager._trigger_manager = FakeTriggerManager()

        self.ctxt = context.get_admin_context()
        self._trigger = self._create_one_trigger()
        self._operation = self._create_scheduled_operation(self._trigger.id)

    def test_init_host(self):
        trigger_id = self._trigger.id
        operation_id = self._operation.id

        self._create_operation_state(operation_id)
        self.manager._restore()

        trigger_manager = self.manager._trigger_manager
        self.assertTrue(trigger_id in trigger_manager._trigger)
        self.assertTrue(operation_id in trigger_manager._trigger[trigger_id])

    def test_create_operation(self):
        operation_id = "1234"
        self.manager.create_scheduled_operation(
            self.ctxt, operation_id, self._trigger.id)

        state_obj = objects.ScheduledOperationState.get_by_operation_id(
            self.ctxt, operation_id)

        self.assertTrue(state_obj is not None)

    def test_delete_operation_get_state_failed(self):
        self.assertRaises(rpc_dispatcher.ExpectedException,
                          self.manager.delete_scheduled_operation,
                          self.ctxt, self._operation.id, 1)

    def test_delete_operation(self):
        state = self._create_operation_state(self._operation.id)

        self.manager.delete_scheduled_operation(
            self.ctxt, self._operation.id, 1)

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.ctxt, self._operation.id)
        self.assertEqual(scheduled_operation_state.DELETED, state.state)

    def _create_one_trigger(self):
        trigger_info = {
            'project_id': "123",
            "name": "123",
            "type": "time",
            "properties": {
                "format": "crontab",
                "pattern": "* * * * *"
            },
        }
        trigger = objects.Trigger(self.ctxt, **trigger_info)
        trigger.create()
        return trigger

    def _create_scheduled_operation(self, trigger_id):
        operation_info = {
            "name": "123",
            "operation_type": "protect",
            "project_id": "123",
            "trigger_id": trigger_id,
            "operation_definition": {
                "plan_id": ""
            },
        }
        operation = objects.ScheduledOperation(self.ctxt, **operation_info)
        operation.create()
        return operation

    def _create_operation_state(self, operation_id):
        state_info = {
            "operation_id": operation_id,
            "service_id": self.manager._service_id,
            "state": scheduled_operation_state.REGISTERED
        }
        operation_state = objects.ScheduledOperationState(context,
                                                          **state_info)
        operation_state.create()
        return operation_state
