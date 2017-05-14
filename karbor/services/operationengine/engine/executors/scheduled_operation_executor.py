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

from abc import abstractmethod
from datetime import datetime
from datetime import timedelta
from oslo_log import log as logging
from oslo_utils import timeutils

from karbor.common import constants
from karbor import context
from karbor import objects
from karbor.services.operationengine.engine.executors import base


LOG = logging.getLogger(__name__)


class ScheduledOperationExecutor(base.BaseExecutor):

    _CHECK_ITEMS = {
        'is_waiting': 'is_waiting',
        'is_canceled': 'is_canceled'
    }

    def execute_operation(self, operation_id, triggered_time,
                          expect_start_time, window_time, **kwargs):

        if self._check_operation(operation_id, self._CHECK_ITEMS.values()):
            LOG.warning("Execute operation(%s), it can't be executed",
                        operation_id)
            return

        end_time_for_run = expect_start_time + timedelta(seconds=window_time)
        ret = self._update_operation_state(
            operation_id,
            {'state': constants.OPERATION_STATE_TRIGGERED,
             'end_time_for_run': end_time_for_run})
        if not ret:
            return

        param = {
            'operation_id': operation_id,
            'triggered_time': triggered_time,
            'expect_start_time': expect_start_time,
            'window_time': window_time,
            'run_type': constants.OPERATION_RUN_TYPE_EXECUTE
        }
        self._execute_operation(operation_id, self._run_operation, param)

    def resume_operation(self, operation_id, **kwargs):
        end_time = kwargs.get('end_time_for_run')
        now = datetime.utcnow()
        if not isinstance(end_time, datetime) or now > end_time:
            return

        window = int(timeutils.delta_seconds(now, end_time))
        param = {
            'operation_id': operation_id,
            'triggered_time': now,
            'expect_start_time': now,
            'window_time': window,
            'run_type': constants.OPERATION_RUN_TYPE_RESUME
        }
        self._execute_operation(operation_id, self._run_operation, param)

    def _run_operation(self, operation_id, param):

        self._update_operation_state(
            operation_id,
            {'state': constants.OPERATION_STATE_RUNNING})

        try:
            check_item = [self._CHECK_ITEMS['is_canceled']]
            if self._check_operation(operation_id, check_item):
                return

            try:
                operation = objects.ScheduledOperation.get_by_id(
                    context.get_admin_context(), operation_id)
            except Exception:
                LOG.exception("Run operation(%s), get operation failed",
                              operation_id)
                return

            try:
                param['user_id'] = operation.user_id
                param['project_id'] = operation.project_id

                self._operation_manager.run_operation(
                    operation.operation_type,
                    operation.operation_definition,
                    param=param)
            except Exception:
                LOG.exception("Run operation(%s) failed", operation_id)

        finally:
            self._update_operation_state(
                operation_id,
                {'state': constants.OPERATION_STATE_REGISTERED})

    def _update_operation_state(self, operation_id, updates):

        ctxt = context.get_admin_context()
        try:
            state_ref = objects.ScheduledOperationState.get_by_operation_id(
                ctxt, operation_id)
            for item, value in updates.items():
                setattr(state_ref, item, value)
            state_ref.save()
        except Exception:
            LOG.exception("Execute operation(%s), update state failed",
                          operation_id)
            return False
        return True

    @abstractmethod
    def _execute_operation(self, operation_id, funtion, param):
        pass

    @abstractmethod
    def _check_operation(self, operation_id, check_items):
        """Check whether the item in check_items happens"""
        pass
