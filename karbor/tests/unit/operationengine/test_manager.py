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
from oslo_messaging.rpc import dispatcher as rpc_dispatcher

from karbor.common import constants
from karbor import context
from karbor import exception
from karbor import objects
from karbor.services.operationengine import manager as service_manager
from karbor.tests import base


class FakeTriggerManager(object):

    def __init__(self):
        super(FakeTriggerManager, self).__init__()
        self._trigger = {}

    def register_operation(self, trigger_id, operation_id, **kwargs):
        if trigger_id not in self._trigger:
            self._trigger[trigger_id] = []

        if operation_id in self._trigger[trigger_id]:
            raise exception.ScheduledOperationExist(op_id=operation_id)

        self._trigger[trigger_id].append(operation_id)

    def unregister_operation(self, trigger_id, operation_id, **kwargs):
        pass

    def add_trigger(self, trigger_id, trigger_type, trigger_property):
        self._trigger[trigger_id] = []


class FakeUserTrustManager(object):
    def add_operation(self, context, operation_id):
        return "123"

    def delete_operation(self, context, operation_id):
        pass

    def resume_operation(self, operation_id, user_id, project_id, trust_id):
        pass


class OperationEngineManagerTestCase(base.TestCase):
    """Test cases for OperationEngineManager class."""

    def setUp(self):
        super(OperationEngineManagerTestCase, self).setUp()

        self.manager = service_manager.OperationEngineManager()
        self.manager._service_id = 0
        self.manager._trigger_manager = FakeTriggerManager()
        self.manager._user_trust_manager = FakeUserTrustManager()

        self.ctxt = context.get_admin_context()
        self._trigger = self._create_one_trigger()
        self._operation = self._create_scheduled_operation(self._trigger.id)

    def test_init_host(self):
        trigger_id = self._trigger.id
        operation_id = self._operation.id

        self._create_operation_state(operation_id)

        op = self._create_scheduled_operation(self._trigger.id, False)
        self._create_operation_state(op.id)

        self.manager._restore()

        trigger_manager = self.manager._trigger_manager
        self.assertIn(trigger_id, trigger_manager._trigger)
        self.assertIn(operation_id, trigger_manager._trigger[trigger_id])
        self.assertNotIn(op.id, trigger_manager._trigger[trigger_id])

    def test_create_operation(self):
        op = self._create_scheduled_operation(self._trigger.id, False)
        with mock.patch(
            'karbor.services.operationengine.operations.protect_operation.'
            'ProtectOperation.check_operation_definition'
        ):
            self.manager.create_scheduled_operation(
                self.ctxt, op)

        state_obj = objects.ScheduledOperationState.get_by_operation_id(
            self.ctxt, op.id)

        self.assertIsNotNone(state_obj)

    def test_create_operation_invalid_operation_definition(self):
        op = self._create_scheduled_operation(self._trigger.id, False)
        self.assertRaises(
            rpc_dispatcher.ExpectedException,
            self.manager.create_scheduled_operation,
            self.ctxt,
            op,
        )

    def test_create_operation_invalid_operation_type(self):
        op = self._create_scheduled_operation(self._trigger.id, False)
        op.operation_type = "123"
        self.assertRaises(
            rpc_dispatcher.ExpectedException,
            self.manager.create_scheduled_operation,
            self.ctxt,
            op,
        )

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
        self.assertEqual(constants.OPERATION_STATE_DELETED, state.state)

    @mock.patch.object(FakeTriggerManager, 'unregister_operation')
    def test_suspend_resume_operation(self, unregister):
        op_id = 'suspend'
        trigger_id = "trigger"

        self.manager.resume_scheduled_operation(self.ctxt, op_id, trigger_id)
        self.assertIn(op_id,
                      self.manager._trigger_manager._trigger[trigger_id])

        self.manager.resume_scheduled_operation(self.ctxt, op_id, trigger_id)
        self.assertEqual(1, len(
            self.manager._trigger_manager._trigger[trigger_id]))

        # resume
        self.manager.suspend_scheduled_operation(self.ctxt, op_id, trigger_id)
        unregister.assert_called_once_with(trigger_id, op_id)

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

    def _create_scheduled_operation(self, trigger_id, enabled=True):
        operation_info = {
            "name": "123",
            'description': '123',
            "operation_type": "protect",
            'user_id': '123',
            "project_id": "123",
            "trigger_id": trigger_id,
            "operation_definition": {
                "plan_id": ""
            },
            "enabled": enabled
        }
        operation = objects.ScheduledOperation(self.ctxt, **operation_info)
        operation.create()
        return operation

    def _create_operation_state(self, operation_id):
        state_info = {
            "operation_id": operation_id,
            "service_id": self.manager._service_id,
            'trust_id': '123',
            "state": constants.OPERATION_STATE_REGISTERED
        }
        operation_state = objects.ScheduledOperationState(context,
                                                          **state_info)
        operation_state.create()
        return operation_state
