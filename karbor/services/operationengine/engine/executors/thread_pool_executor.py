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

from collections import defaultdict
from concurrent import futures
from oslo_config import cfg
from oslo_log import log as logging
from threading import RLock

from karbor.services.operationengine.engine.executors import \
    scheduled_operation_executor as base_executor

executor_opts = [
    cfg.IntOpt('thread_count',
               default=10,
               help='The count of thread which executor will start')
]

CONF = cfg.CONF
CONF.register_opts(executor_opts)

LOG = logging.getLogger(__name__)


class ThreadPoolExecutor(base_executor.ScheduledOperationExecutor):

    def __init__(self, operation_manager, thread_count=None):
        super(ThreadPoolExecutor, self).__init__(operation_manager)

        if thread_count is None:
            thread_count = CONF.thread_count

        self._pool = futures.ThreadPoolExecutor(thread_count)
        self._operation_to_run = defaultdict(int)
        self._operation_to_cancel = set()
        self._lock = RLock()

        self._check_functions = {
            self._CHECK_ITEMS['is_waiting']: lambda op_id: (
                op_id in self._operation_to_run),

            self._CHECK_ITEMS['is_canceled']: lambda op_id: (
                op_id in self._operation_to_cancel),
        }

    def shutdown(self, wait=True):
        self._pool.shutdown(wait)
        self._operation_to_run.clear()
        self._operation_to_cancel.clear()

    def cancel_operation(self, operation_id):
        with self._lock:
            if operation_id in self._operation_to_run:
                self._operation_to_cancel.add(operation_id)

    def _check_operation(self, operation_id, check_items):
        with self._lock:
            return any(self._check_functions[item](operation_id)
                       for item in check_items)

    def _execute_operation(self, operation_id, function, param):

        def callback(f):
            self._finish_operation(operation_id)

        with self._lock:
            self._operation_to_run[operation_id] += 1

            try:
                f = self._pool.submit(function, operation_id, param)
                f.add_done_callback(callback)

            except Exception:
                self._operation_to_run[operation_id] -= 1
                LOG.exception("Submit operation(%(o_id)s) failed.",
                              operation_id)

    def _finish_operation(self, operation_id):
        with self._lock:
            self._operation_to_run[operation_id] -= 1
            if 0 == self._operation_to_run[operation_id]:
                del self._operation_to_run[operation_id]

                if operation_id in self._operation_to_cancel:
                    self._operation_to_cancel.remove(operation_id)
