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
Executor which receives operations and run them.
"""

from abc import ABCMeta
from abc import abstractmethod
import six


@six.add_metaclass(ABCMeta)
class BaseExecutor(object):
    def __init__(self, operation_manager):
        self._operation_manager = operation_manager
        super(BaseExecutor, self).__init__()

    @abstractmethod
    def execute_operation(self, operation_id, triggered_time,
                          expect_start_time, window_time, **kwargs):
        """Execute an operation.

        :param operation_id: ID of operation
        :param triggered_time: time when the operation is triggered
        :param expect_start_time: expect time when to run the operation
        :param window_time: time how long to wait to run the operation after
                      expect_start_time
        """
        pass

    @abstractmethod
    def cancel_operation(self, operation_id):
        """Cancel the execution of operation.

        There is no effective for the operations which are running, but
        for operations which are in waiting, they will not be executed.

        :param operation_id: ID of operation
        """
        pass

    @abstractmethod
    def resume_operation(self, operation_id, **kwargs):
        """Resume operations.

        Get operations which are not finished from DB by operation_id,
        and execute them again.

        :param operation_id: ID of operation
        """
        pass

    @abstractmethod
    def shutdown(self):
        """Shutdown the executor"""
        pass
