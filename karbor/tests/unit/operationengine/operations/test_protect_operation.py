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
import mock

from karbor.common import constants
from karbor import context
from karbor import exception
from karbor import objects
from karbor.services.operationengine.operations import base as base_operation
from karbor.services.operationengine.operations import protect_operation
from karbor.tests import base


class FakeUserTrustManager(object):
    def add_operation(self, context, operation_id):
        return "123"

    def delete_operation(self, context, operation_id):
        pass

    def resume_operation(self, operation_id, user_id, project_id, trust_id):
        pass


class FakeCheckPoint(object):
    def create(self, provider_id, plan_id):
        return


class FakeKarborClient(object):
    def __init__(self):
        super(FakeKarborClient, self).__init__()
        self._check_point = FakeCheckPoint()

    @property
    def checkpoints(self):
        return self._check_point


class ProtectOperationTestCase(base.TestCase):
    """Test cases for ProtectOperation class."""

    def setUp(self):
        super(ProtectOperationTestCase, self).setUp()
        self._user_trust_manager = FakeUserTrustManager()
        self._operation = protect_operation.ProtectOperation(
            self._user_trust_manager
        )
        self._operation_db = self._create_operation()
        self._fake_karbor_client = FakeKarborClient()

    def test_check_operation_definition(self):
        self.assertRaises(exception.InvalidOperationDefinition,
                          self._operation.check_operation_definition,
                          {})

    @mock.patch.object(base_operation.Operation, '_create_karbor_client')
    def test_execute(self, client):
        client.return_value = self._fake_karbor_client
        now = datetime.utcnow()
        param = {
            'operation_id': self._operation_db.id,
            'triggered_time': now,
            'expect_start_time': now,
            'window_time': 30,
            'run_type': constants.OPERATION_RUN_TYPE_EXECUTE,
            'user_id': self._operation_db.user_id,
            'project_id': self._operation_db.project_id
        }
        self._operation.run(self._operation_db.operation_definition,
                            param=param)

        logs = objects.ScheduledOperationLogList.get_by_filters(
            context.get_admin_context(),
            {'state': constants.OPERATION_EXE_STATE_SUCCESS,
             'operation_id': self._operation_db.id}, 1,
            None, ['created_at'], ['desc'])

        self.assertIsNotNone(logs)
        log = logs.objects[0]
        self.assertTrue(now, log.triggered_time)

    @mock.patch.object(base_operation.Operation, '_create_karbor_client')
    def test_resume(self, client):
        log = self._create_operation_log(self._operation_db.id)
        client.return_value = self._fake_karbor_client
        now = datetime.utcnow()
        param = {
            'operation_id': self._operation_db.id,
            'triggered_time': now,
            'expect_start_time': now,
            'window_time': 30,
            'run_type': constants.OPERATION_RUN_TYPE_RESUME,
            'user_id': self._operation_db.user_id,
            'project_id': self._operation_db.project_id
        }
        self._operation.run(self._operation_db.operation_definition,
                            param=param)

        logs = objects.ScheduledOperationLogList.get_by_filters(
            context.get_admin_context(),
            {'state': constants.OPERATION_EXE_STATE_SUCCESS,
             'operation_id': self._operation_db.id}, 1,
            None, ['created_at'], ['desc'])

        self.assertIsNotNone(logs)
        log1 = logs.objects[0]
        self.assertTrue(log.id, log1.id)

    def _create_operation(self):
        operation_info = {
            'name': 'protect vm',
            'description': 'protect vm resource',
            'operation_type': 'protect',
            'user_id': '123',
            'project_id': '123',
            'trigger_id': '123',
            'operation_definition': {
                'provider_id': '123',
                'plan_id': '123'
            }
        }
        operation = objects.ScheduledOperation(context.get_admin_context(),
                                               **operation_info)
        operation.create()
        return operation

    def _create_operation_log(self, operation_id):
        log_info = {
            'operation_id': operation_id,
            'state': constants.OPERATION_EXE_STATE_IN_PROGRESS,
        }
        log = objects.ScheduledOperationLog(context.get_admin_context(),
                                            **log_info)
        log.create()
        return log
