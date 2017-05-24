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
Operation classes
"""
import abc
import six

from abc import ABCMeta
from datetime import datetime
from datetime import timedelta
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import constants
from karbor import context
from karbor import objects
from karbor.services.operationengine import karbor_client


record_operation_log_executor_opts = [
    cfg.IntOpt(
        'retained_operation_log_number',
        default=5,
        help='The number of retained operation log')
]

CONF = cfg.CONF
CONF.register_opts(record_operation_log_executor_opts)

LOG = logging.getLogger(__name__)


@six.add_metaclass(ABCMeta)
class Operation(object):
    OPERATION_TYPE = ""

    def __init__(self, user_trust_manager):
        super(Operation, self).__init__()
        self._user_trust_manager = user_trust_manager
        self._karbor_endpoint = None

    @abc.abstractmethod
    def check_operation_definition(self, operation_definition):
        """Check operation definition

        :param operation_definition: the definition of operation
        """
        pass

    @property
    def karbor_endpoint(self):
        if not self._karbor_endpoint:
            self._karbor_endpoint = karbor_client.get_karbor_endpoint()
        return self._karbor_endpoint

    def run(self, operation_definition, **kwargs):
        param = kwargs.get('param')
        operation_id = param.get('operation_id')
        window = param.get('window_time')
        end_time = param['expect_start_time'] + timedelta(seconds=window)
        is_operation_expired = datetime.utcnow() > end_time

        if constants.OPERATION_RUN_TYPE_RESUME == param['run_type']:
            log_ref = self._get_operation_log(
                operation_id, constants.OPERATION_EXE_STATE_IN_PROGRESS)

            if log_ref is None or len(log_ref) > 1:
                return

            if 1 == len(log_ref):
                log = log_ref[0]
                if is_operation_expired:
                    self._update_log_when_operation_finished(
                        log,
                        constants.OPERATION_EXE_STATE_DROPPED_OUT_OF_WINDOW)
                else:
                    self._resume(operation_definition, param, log)

                self._delete_oldest_operation_log(operation_id)
                return

        if is_operation_expired:
            log_info = {
                'state': constants.OPERATION_EXE_STATE_DROPPED_OUT_OF_WINDOW,
                'end_time': datetime.utcnow()
            }
            log_ref = self._create_operation_log(param, log_info)
        else:
            self._execute(operation_definition, param)

        self._delete_oldest_operation_log(operation_id)

    @abc.abstractmethod
    def _execute(self, operation_definition, param):
        """Execute operation.

        :param operation_definition: the definition of operation
        :param param: dict, other parameters
        """
        pass

    @abc.abstractmethod
    def _resume(self, operation_definition, param, log_ref):
        """Resume operation.

        :param operation_definition: the definition of operation
        :param param: dict, other parameters
        :param log_ref: instance of ScheduledOperationLog
        """
        pass

    def _create_operation_log(self, param, updated_log_info=None):
        log_info = {
            'operation_id': param['operation_id'],
            'expect_start_time': param['expect_start_time'],
            'triggered_time': param['triggered_time'],
            'actual_start_time': datetime.utcnow(),
            'state': constants.OPERATION_EXE_STATE_IN_PROGRESS
        }
        if updated_log_info:
            log_info.update(updated_log_info)

        log_ref = objects.ScheduledOperationLog(context.get_admin_context(),
                                                **log_info)
        try:
            log_ref.create()
        except Exception:
            LOG.exception("Execute operation(%s), create log obj failed",
                          param['operation_id'])
            return
        return log_ref

    def _delete_oldest_operation_log(self, operation_id):
        # delete the oldest logs to keep the number of logs
        # in a reasonable range
        try:
            objects.ScheduledOperationLog.destroy_oldest(
                context.get_admin_context(), operation_id,
                CONF.retained_operation_log_number)
        except Exception:
            pass

    def _update_operation_log(self, log_ref, updates):
        if not log_ref:
            return

        for item in updates:
            setattr(log_ref, item, updates.get(item))
        try:
            log_ref.save()
        except Exception:
            LOG.exception("Execute operation(%s), save log failed",
                          log_ref.operation_id)

    def _update_log_when_operation_finished(self, log_ref, state,
                                            updated_log_info=None):
        if not log_ref:
            return

        updates = {
            'state': state,
            'end_time': datetime.utcnow()
        }
        if updated_log_info:
            updates.update(updated_log_info)

        self._update_operation_log(log_ref, updates)

    def _get_operation_log(self, operation_id, operation_state):
        try:
            logs = objects.ScheduledOperationLogList.get_by_filters(
                context.get_admin_context(),
                {'state': operation_state,
                 'operation_id': operation_id}, limit=2)

            return logs.objects
        except Exception:
            pass

    def _create_karbor_client(self, user_id, project_id):
        token = self._user_trust_manager.get_token(user_id, project_id)
        if not token:
            return None
        ctx = context.get_admin_context()
        ctx.auth_token = token
        ctx.project_id = project_id

        karbor_url = self.karbor_endpoint % {"project_id": project_id}
        return karbor_client.create(ctx, endpoint=karbor_url)
