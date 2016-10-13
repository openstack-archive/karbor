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

        mock_obj = mock.Mock()
        mock_obj.return_value = [FakeOperation]
        operations.all_operations = mock_obj

        self._operation_type = FakeOperation.OPERATION_TYPE
        self.om = operation_manager.OperationManager()

    def test_singleton_operation_manager(self):
        second = operation_manager.OperationManager()
        self.assertTrue(self.om == second)

    def test_load_all_class(self):
        self.assertIn(self._operation_type, self.om._operation_cls_map)

    @mock.patch.object(FakeOperation, 'check_operation_definition')
    def test_check_operation_definition(self, check):
        self.om.check_operation_definition(self._operation_type, {})
        check.assert_called_once_with({})

    @mock.patch.object(operations.base.Operation, 'run')
    def test_run_operation(self, run):
        self.om.run_operation(self._operation_type, {})
        run.assert_called_once_with({})

    def test_invalid_operation_type(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               'Invalid operation type:',
                               self.om.check_operation_definition,
                               "123", {})

        self.assertRaisesRegex(exception.InvalidInput,
                               'Invalid operation type:',
                               self.om.run_operation,
                               "123", {})
