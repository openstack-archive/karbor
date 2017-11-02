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

from karbor.common import constants
from karbor import context
from karbor import exception
from karbor import objects
from karbor.services.operationengine.operations import base as base_operation
from karbor.services.operationengine.operations import retention_operation
from karbor.tests import base


class FakeUserTrustManager(object):
    def add_operation(self, context, operation_id):
        return "123"

    def delete_operation(self, context, operation_id):
        pass

    def resume_operation(self, operation_id, user_id, project_id, trust_id):
        pass


class FakeCheckPointInstance(object):
    def __init__(self, id, created_at):
        super(FakeCheckPointInstance, self).__init__()
        self.id = id
        self.created_at = created_at
        self.status = 'available'
        self.project_id = '123'
        self.protection_plan = {
            'provider_id': '123',
            'id': '123',
            'resources': None,
            'name': 'protect vm resource'
        }


class FakeCheckPoint(object):

    _checkpoints = []

    def __init__(self):
        super(FakeCheckPoint, self).__init__()

    def create_all_check_points(self):
        now = datetime.utcnow()
        d1 = now - timedelta(days=16)
        d2 = now - timedelta(days=15)
        d3 = now - timedelta(days=3)
        self._checkpoints.insert(
            0, FakeCheckPointInstance("1", d1.strftime("%Y-%m-%d")))
        self._checkpoints.insert(
            0, FakeCheckPointInstance("2", d2.strftime("%Y-%m-%d")))
        self._checkpoints.insert(
            0, FakeCheckPointInstance("3", d3.strftime("%Y-%m-%d")))

    def create(self, provider_id, plan_id, extra_info):
        now = datetime.utcnow()
        self._checkpoints.insert(
            0, FakeCheckPointInstance("4", now.strftime("%Y-%m-%d")))

    def delete(self, provider_id, checkpoint_id):
        self._checkpoints = [x for x in self._checkpoints if x.id !=
                             checkpoint_id]

    def list(self, provider_id, search_opts=None, limit=None, sort=None):
        return self._checkpoints


class FakeKarborClient(object):
    def __init__(self):
        super(FakeKarborClient, self).__init__()
        self._check_point = FakeCheckPoint()

    @property
    def checkpoints(self):
        return self._check_point

    def create_all_check_points(self):
        self._check_point.create_all_check_points()


class ProtectOperationTestCase(base.TestCase):
    """Test cases for ProtectOperation class."""

    def setUp(self):
        super(ProtectOperationTestCase, self).setUp()
        self._user_trust_manager = FakeUserTrustManager()
        self._operation = retention_operation.RetentionProtectOperation(
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
        self._fake_karbor_client.create_all_check_points()
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
            {'state': constants.OPERATION_EXE_DURATION_STATE_SUCCESS,
             'operation_id': self._operation_db.id}, 1,
            None, ['created_at'], ['desc'])
        self.assertIsNotNone(logs)
        log = logs.objects[0]
        self.assertTrue(now, log.triggered_time)
        checkpoints = self._fake_karbor_client.checkpoints.list("123")
        self.assertEqual(2, len(checkpoints))

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
            {'state': constants.OPERATION_EXE_DURATION_STATE_SUCCESS,
             'operation_id': self._operation_db.id}, 1,
            None, ['created_at'], ['desc'])

        self.assertIsNotNone(logs)
        log1 = logs.objects[0]
        self.assertTrue(log.id, log1.id)

    def _create_operation(self):
        operation_info = {
            'name': 'protect vm',
            'description': 'protect vm resource',
            'operation_type': 'retention_protect',
            'user_id': '123',
            'project_id': '123',
            'trigger_id': '123',
            'operation_definition': {
                'max_backups': '3',
                'provider_id': '123',
                'plan_id': '123',
                'retention_duration': '14'
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
