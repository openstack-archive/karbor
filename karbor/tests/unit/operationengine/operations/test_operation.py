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

from datetime import datetime
from datetime import timedelta

from karbor.common import constants
from karbor.common import karbor_keystone_plugin
from karbor import context
from karbor import objects
from karbor.services.operationengine.operations import base as base_operation
from karbor.services.operationengine import user_trust_manager
from karbor.tests import base


class OperationTestCase(base.TestCase):
    """Test cases for ProtectOperation class."""

    def setUp(self):
        super(OperationTestCase, self).setUp()
        self._operation_class = base_operation.Operation
        self._operation_db = self._create_operation()

    def test_run_execute(self):
        now = datetime.utcnow() - timedelta(hours=1)
        param = {
            'operation_id': self._operation_db.id,
            'triggered_time': now,
            'expect_start_time': now,
            'window_time': 30,
            'run_type': constants.OPERATION_RUN_TYPE_EXECUTE,
            'user_id': self._operation_db.user_id,
            'project_id': self._operation_db.project_id
        }
        self._operation_class.run(self._operation_db.operation_definition,
                                  param=param)

        logs = objects.ScheduledOperationLogList.get_by_filters(
            context.get_admin_context(),
            {'state': constants.OPERATION_EXE_STATE_DROPPED_OUT_OF_WINDOW,
             'operation_id': self._operation_db.id}, 1,
            None, ['created_at'], ['desc'])

        self.assertTrue(logs is not None)
        log = logs.objects[0]
        self.assertTrue(now, log.triggered_time)

    def test_run_resume(self):
        log = self._create_operation_log(self._operation_db.id)
        now = datetime.utcnow() - timedelta(hours=1)
        param = {
            'operation_id': self._operation_db.id,
            'triggered_time': now,
            'expect_start_time': now,
            'window_time': 30,
            'run_type': constants.OPERATION_RUN_TYPE_RESUME,
            'user_id': self._operation_db.user_id,
            'project_id': self._operation_db.project_id
        }
        self._operation_class.run(self._operation_db.operation_definition,
                                  param=param)

        logs = objects.ScheduledOperationLogList.get_by_filters(
            context.get_admin_context(),
            {'state': constants.OPERATION_EXE_STATE_DROPPED_OUT_OF_WINDOW,
             'operation_id': self._operation_db.id}, 1,
            None, ['created_at'], ['desc'])

        self.assertTrue(logs is not None)
        log1 = logs.objects[0]
        self.assertTrue(log.id, log1.id)

    def test_create_karbor_client(self):
        self._operation_class.KARBOR_ENDPOINT = 'http://127.0.0.0'
        cls = user_trust_manager.UserTrustManager
        cls1 = karbor_keystone_plugin.KarborKeystonePlugin
        with mock.patch.object(cls1, '_do_init'):
            with mock.patch.object(cls, 'get_token') as get_token:
                get_token.return_value = 'abc'
                with mock.patch('karbor.services.operationengine.'
                                'karbor_client.create') as create:
                    self._operation_class._create_karbor_client(
                        'abc', 'def')
                    create.assert_called_once()

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
