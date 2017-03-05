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

from karbor import exception
from karbor.services.operationengine import operation_manager
from karbor.services.operationengine import operations
from karbor.tests import base


class FakeUserTrustManager(object):
    def add_operation(self, context, operation_id):
        return "123"

    def delete_operation(self, context, operation_id):
        pass

    def resume_operation(self, operation_id, user_id, project_id, trust_id):
        pass


class FakeOperation(operations.base.Operation):
    OPERATION_TYPE = 'fake'

    @classmethod
    def check_operation_definition(cls, operation_definition):
        pass

    @classmethod
    def _execute(cls, operation_definition, param):
        pass

    @classmethod
    def _resume(cls, operation_definition, param, log_ref):
        pass


class OperationManagerTestCase(base.TestCase):
    """Test cases for OperationManager class."""

    def setUp(self):
        super(OperationManagerTestCase, self).setUp()

        self._operation_type = FakeOperation.OPERATION_TYPE
        self._mock_operations = (FakeOperation, )
        with mock.patch(
            'karbor.services.operationengine.operations.all_operations'
        ) as mock_all_ops:
            mock_all_ops.return_value = self._mock_operations
            self._user_trust_manager = FakeUserTrustManager()
            self._op_manager = operation_manager.OperationManager(
                self._user_trust_manager)

    @mock.patch.object(FakeOperation, 'check_operation_definition')
    def test_check_operation_definition(self, mock_check):
        self._op_manager.check_operation_definition(self._operation_type, {})
        mock_check.assert_called_once_with({})

    @mock.patch.object(operations.base.Operation, 'run')
    def test_run_operation(self, mock_run):
        self._op_manager.run_operation(self._operation_type, {})
        mock_run.assert_called_once_with({})

    def test_invalid_operation_type(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               'Invalid operation type:',
                               self._op_manager.check_operation_definition,
                               "123", {})

        self.assertRaisesRegex(exception.InvalidInput,
                               'Invalid operation type:',
                               self._op_manager.run_operation,
                               "123", {})
