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

from datetime import datetime
from datetime import timedelta
import mock
import time

from smaug.common import constants
from smaug import context
from smaug import objects
from smaug.services.operationengine.engine.executors import\
    thread_pool_executor
from smaug.tests import base

NOW = datetime.utcnow()
Log_ID = 0
Operation_ID = "123"

Fake_Log = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    'id': Log_ID,
    'operation_id': Operation_ID,
    'expect_start_time': NOW,
    'triggered_time': NOW,
    'actual_start_time': NOW,
    'end_time': NOW,
    'state': 'in_progress',
    'extend_info': '',
}

Fake_Operation = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    'id': Operation_ID,
    'name': 'protect vm',
    'operation_type': 'protect',
    'project_id': '123',
    'trigger_id': '0354ca9ddcd046b693340d78759fd275',
    'operation_definition': '{}'
}


class ThreadPoolExecutorTestCase(base.TestCase):

    def setUp(self):
        super(ThreadPoolExecutorTestCase, self).setUp()

        self._executor = thread_pool_executor.ThreadPoolExecutor()
        self.context = context.get_admin_context()

    def tearDown(self):
        super(ThreadPoolExecutorTestCase, self).tearDown()
        self._executor.shutdown()

    @mock.patch('smaug.services.operationengine.operations.'
                'protect_operation.ProtectOperation._execute')
    def test_execute_operation(self, execute):
        operation = self._create_operation()
        self._create_operation_state(operation.id, 0)

        now = datetime.utcnow()
        window_time = 30

        self._executor.execute_operation(operation.id, now, now, window_time)

        time.sleep(1)

        self.assertEqual(0, len(self._executor._operation_to_run))

        param = {
            'operation_id': operation.id,
            'triggered_time': now,
            'expect_start_time': now,
            'window_time': window_time,
            'run_type': constants.OPERATION_RUN_TYPE_EXECUTE
        }
        execute.assert_called_once_with(
            operation.project_id, operation.operation_definition, param)

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.context, operation.id)
        self.assertTrue(state.end_time_for_run is not None)
        self.assertTrue(constants.OPERATION_STATE_REGISTERED == state.state)

    @mock.patch('smaug.services.operationengine.operations.'
                'protect_operation.ProtectOperation._resume')
    def test_resume_operation(self, resume):
        operation = self._create_operation()
        self._create_operation_state(operation.id, 0)

        now = datetime.utcnow()
        window_time = 30

        self._executor.resume_operation(operation.id, end_time_for_run=(
            now + timedelta(seconds=window_time)))

        time.sleep(1)

        self.assertEqual(0, len(self._executor._operation_to_run))

        self.assertTrue(resume.called)

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.context, operation.id)
        self.assertTrue(constants.OPERATION_STATE_REGISTERED == state.state)

    def test_cancel_operation(self):
        operation_id = '123'

        self._executor.cancel_operation(operation_id)
        self.assertEqual(0, len(self._executor._operation_to_cancel))

        self._executor._operation_to_run[operation_id] = 0
        self._executor.cancel_operation(Operation_ID)
        self.assertEqual(1, len(self._executor._operation_to_cancel))

    def _create_operation(self, trigger_id='123'):
        operation_info = {
            'name': 'protect vm',
            'operation_type': 'protect',
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
            'state': constants.OPERATION_STATE_INIT,
        }
        state = objects.ScheduledOperationState(self.context, **state_info)
        state.create()
        return state
