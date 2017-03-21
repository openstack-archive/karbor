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

import eventlet
import greenlet

from datetime import datetime
from datetime import timedelta
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from karbor.common import constants
from karbor import context
from karbor import objects
from karbor.services.operationengine.engine.executors import base


green_thread_executor_opts = [
    cfg.IntOpt('max_concurrent_operations',
               default=0,
               help='number of maximum concurrent running operations,'
                    '0 means no hard limit'
               )
]

CONF = cfg.CONF
CONF.register_opts(green_thread_executor_opts, 'operationengine')

LOG = logging.getLogger(__name__)


class GreenThreadExecutor(base.BaseExecutor):

    def __init__(self, operation_manager):
        super(GreenThreadExecutor, self).__init__(operation_manager)
        self._operation_thread_map = {}

    def execute_operation(self, operation_id, triggered_time,
                          expect_start_time, window_time, **kwargs):

        if operation_id in self._operation_thread_map:
            LOG.warning("Execute operation(%s), the previous one has not been"
                        " finished", operation_id)
            return

        num = CONF.operationengine.max_concurrent_operations
        if num and len(self._operation_thread_map) >= num:
            LOG.warning("The amount of concurrent running operations "
                        "exceeds %d", num)
            return
        self._operation_thread_map[operation_id] = None

        end_time_for_run = expect_start_time + timedelta(seconds=window_time)
        ret = self._update_operation_state(
            operation_id,
            {'state': constants.OPERATION_STATE_TRIGGERED,
             'end_time_for_run': end_time_for_run})
        if not ret:
            self._operation_thread_map.pop(operation_id, None)
            return

        if operation_id not in self._operation_thread_map:
            # This function is invoked by trigger which may runs in the
            # green thread. So if operation_id is not exist, it may be
            # canceled by 'cancel_operation' during the call to DB in
            # the codes above.
            LOG.warning("Operation(%s) is not exist after call to DB",
                        operation_id)
            return

        param = {
            'operation_id': operation_id,
            'triggered_time': triggered_time,
            'expect_start_time': expect_start_time,
            'window_time': window_time,
            'run_type': constants.OPERATION_RUN_TYPE_EXECUTE
        }
        try:
            self._create_thread(self._run_operation, operation_id, param)
        except Exception:
            self._operation_thread_map.pop(operation_id, None)
            LOG.exception("Execute operation (%s), and create green thread "
                          "failed", operation_id)

    def cancel_operation(self, operation_id):
        gt = self._operation_thread_map.get(operation_id, None)
        if gt is not None:  # can not use 'if gt' instead
            # If the thead has not started, it will be killed;
            # else, it will run until finishes its work.
            gt.cancel()
        else:
            self._operation_thread_map.pop(operation_id, None)

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
        self._create_thread(self._run_operation, operation_id, param)

    def shutdown(self):
        for op_id, gt in self._operation_thread_map.items():
            if gt is None:
                continue

            gt.cancel()
            try:
                gt.wait()  # wait untile the thread finishes its work
            except (greenlet.GreenletExit, Exception):
                pass

        self._operation_thread_map = {}

    def _run_operation(self, operation_id, param):

        self._update_operation_state(
            operation_id,
            {'state': constants.OPERATION_STATE_RUNNING})

        try:
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

    def _on_gt_done(self, gt, *args, **kwargs):
        op_id = args[0]
        try:
            del self._operation_thread_map[op_id]
        except Exception:
            LOG.warning("Unknown operation id(%s) received, "
                        "when the green thread exit", op_id)

    def _create_thread(self, function, operation_id, param):
        gt = eventlet.spawn(function, operation_id, param)
        self._operation_thread_map[operation_id] = gt
        gt.link(self._on_gt_done, operation_id)
