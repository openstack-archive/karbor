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
import time

from karbor.common import constants
from karbor import context
from karbor import objects
from karbor.services.operationengine.engine.executors import \
    thread_pool_executor
from karbor.tests import base


class FakeOperationManager(object):
    def run_operation(self, operation_type, operation_definition, **kwargs):
        return


class ThreadPoolExecutorTestCase(base.TestCase):

    def setUp(self):
        super(ThreadPoolExecutorTestCase, self).setUp()

        self._operation_manager = FakeOperationManager()
        self._executor = thread_pool_executor.ThreadPoolExecutor(
            self._operation_manager)
        self.context = context.get_admin_context()

    def tearDown(self):
        super(ThreadPoolExecutorTestCase, self).tearDown()
        self._executor.shutdown()

    def test_execute_operation(self):
        operation = self._create_operation()
        self._create_operation_state(operation.id, 0)

        now = datetime.utcnow()
        window_time = 30

        self._executor.execute_operation(operation.id, now, now, window_time)

        time.sleep(1)

        self.assertEqual(0, len(self._executor._operation_to_run))

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.context, operation.id)
        self.assertIsNotNone(state.end_time_for_run)
        self.assertEqual(constants.OPERATION_STATE_REGISTERED, state.state)

    def test_resume_operation(self):
        operation = self._create_operation()
        self._create_operation_state(operation.id, 0)

        now = datetime.utcnow()
        window_time = 30

        self._executor.resume_operation(operation.id, end_time_for_run=(
            now + timedelta(seconds=window_time)))

        time.sleep(1)

        self.assertEqual(0, len(self._executor._operation_to_run))

        state = objects.ScheduledOperationState.get_by_operation_id(
            self.context, operation.id)
        self.assertEqual(constants.OPERATION_STATE_REGISTERED, state.state)

    def test_cancel_operation(self):
        operation_id = '123'

        self._executor.cancel_operation(operation_id)
        self.assertEqual(0, len(self._executor._operation_to_cancel))

        self._executor._operation_to_run[operation_id] = 0
        self._executor.cancel_operation(operation_id)
        self.assertEqual(1, len(self._executor._operation_to_cancel))

    def _create_operation(self, trigger_id='123'):
        operation_info = {
            'name': 'protect vm',
            'description': 'protect vm resource',
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
