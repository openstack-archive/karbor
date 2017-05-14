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

import eventlet

from datetime import datetime
from datetime import timedelta

from karbor.common import constants
from karbor import context
from karbor import objects
from karbor.services.operationengine.engine.executors import \
    green_thread_executor
from karbor.tests import base


class FakeOperationManager(object):
    def __init__(self):
        super(FakeOperationManager, self).__init__()
        self._op_id = 0

    def run_operation(self, operation_type, operation_definition, **kwargs):
        self._op_id = kwargs['param']['operation_id']
        return


class GreenThreadExecutorTestCase(base.TestCase):

    def setUp(self):
        super(GreenThreadExecutorTestCase, self).setUp()

        self._operation_manager = FakeOperationManager()
        self._executor = green_thread_executor.GreenThreadExecutor(
            self._operation_manager)
        self.context = context.get_admin_context()

        operation = self._create_operation()
        self._create_operation_state(operation.id, 0)
        self._op_id = operation.id

    def tearDown(self):
        self._executor.shutdown()
        super(GreenThreadExecutorTestCase, self).tearDown()

    def test_execute_operation(self):
        now = datetime.utcnow()
        window_time = 30
        self._executor.execute_operation(self._op_id, now, now, window_time)

        self.assertIn(self._op_id, self._executor._operation_thread_map)

        eventlet.sleep(1)

        self.assertTrue(not self._executor._operation_thread_map)

        self.assertEqual(self._op_id, self._operation_manager._op_id)
        self._operation_manager._op_id = ''

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.context, self._op_id)
        self.assertIsNotNone(state.end_time_for_run)
        self.assertEqual(constants.OPERATION_STATE_REGISTERED, state.state)

    def test_resume_operation(self):
        now = datetime.utcnow()
        window_time = 30
        self._executor.resume_operation(self._op_id, end_time_for_run=(
            now + timedelta(seconds=window_time)))

        self.assertIn(self._op_id, self._executor._operation_thread_map)

        eventlet.sleep(1)

        self.assertTrue(not self._executor._operation_thread_map)

        self.assertEqual(self._op_id, self._operation_manager._op_id)
        self._operation_manager._op_id = ''

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.context, self._op_id)
        self.assertEqual(constants.OPERATION_STATE_REGISTERED, state.state)

    def test_cancel_operation(self):
        now = datetime.utcnow()
        window_time = 30
        self._executor.execute_operation(self._op_id, now, now, window_time)

        self.assertIn(self._op_id, self._executor._operation_thread_map)

        self._executor.cancel_operation(self._op_id)

        self.assertTrue(not self._operation_manager._op_id)

        eventlet.sleep(1)

        self.assertTrue(not self._operation_manager._op_id)

    def _create_operation(self, trigger_id='123'):
        operation_info = {
            'name': 'protect vm',
            'operation_type': 'protect',
            'user_id': '123',
            'project_id': '123',
            'trigger_id': trigger_id,
            'operation_definition': {}
        }
        operation = objects.ScheduledOperation(self.context, **operation_info)
        operation.create()
        return operation

    def _create_operation_state(self, operation_id, service_id):
        state_info = {
            'operation_id': operation_id,
            'service_id': service_id,
            'trust_id': '123',
            'state': constants.OPERATION_STATE_INIT,
        }
        state = objects.ScheduledOperationState(self.context, **state_info)
        state.create()
        return state
