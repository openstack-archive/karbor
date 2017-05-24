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

"""
Manage all operations.
"""

from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine import operations


class OperationManager(object):
    """Manage all operation classes which are defined at operations dir."""
    def __init__(self, user_trust_manager):
        super(OperationManager, self).__init__()
        self._user_trust_manager = user_trust_manager
        all_ops = operations.all_operations()
        self._ops_map = {op.OPERATION_TYPE: op(self._user_trust_manager)
                         for op in all_ops}

    def _get_operation(self, operation_type):
        if operation_type not in self._ops_map:
            msg = (_("Invalid operation type: %s") % operation_type)
            raise exception.InvalidInput(msg)

        return self._ops_map[operation_type]

    def check_operation_definition(self, operation_type, operation_definition):
        """Check operation definition.

        :param operation_type: the type of operation
        :param operation_definition: the definition of operation
        :raise InvalidInput if the operation_type is invalid or
               InvalidOperationDefinition if operation_definition is invalid
        """
        op = self._get_operation(operation_type)
        op.check_operation_definition(operation_definition)

    def run_operation(self, operation_type, operation_definition, **kwargs):
        """Run operation.

        :param operation_type: the type of operation
        :param operation_definition: the definition of operation
        :raise InvalidInput if the operation_type is invalid.
        """
        op = self._get_operation(operation_type)
        op.run(operation_definition, **kwargs)
