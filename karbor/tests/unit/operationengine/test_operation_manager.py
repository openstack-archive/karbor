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

from karbor import exception
from karbor.services.operationengine import operation_manager
from karbor.tests import base


class OperationManagerTestCase(base.TestCase):
    """Test cases for OperationManager class."""

    def setUp(self):
        super(OperationManagerTestCase, self).setUp()
        self.om = operation_manager.OperationManager()

    def test_singleton_operation_manager(self):
        second = operation_manager.OperationManager()
        self.assertTrue(self.om == second)

    def test_load_all_class(self):
        self.assertIn("protect", self.om._operation_cls_map)

    def test_invalid_operation_type(self):
        bingo = 0
        try:
            self.om.check_operation_definition("123", {})
        except exception.InvalidInput as ex:
            bingo = 1 if ex.msg.find("operation type") >= 0 else 0

        self.assertEqual(1, bingo)

    def test_invalid_operation_definition(self):
        self.assertRaises(exception.InvalidOperationDefinition,
                          self.om.check_operation_definition,
                          "protect", {})
