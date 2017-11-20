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

from datetime import datetime
from datetime import timedelta

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall

from karbor import context as karbor_context
from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine import triggers
from karbor.services.operationengine.engine.triggers.timetrigger import utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class TimeTrigger(triggers.BaseTrigger):

    TRIGGER_TYPE = "time"
    IS_ENABLED = (CONF.scheduling_strategy == 'multi_node')

    _loopingcall = None
    _triggers = {}

    def __init__(self, trigger_id, trigger_property, executor):
        super(TimeTrigger, self).__init__(
            trigger_id, trigger_property, executor)

        self._trigger_property = self.check_trigger_definition(
            trigger_property)

        timer = self._get_timer(self._trigger_property)
        first_run_time = self._compute_next_run_time(
            datetime.utcnow(), self._trigger_property['end_time'], timer)
        LOG.debug("first_run_time: %s", first_run_time)

        self._trigger_execution_new(self._id, first_run_time)

        if not self.__class__._loopingcall:
            self.__class__._loopingcall = loopingcall.FixedIntervalLoopingCall(
                self._loop)
            self.__class__._loopingcall.start(
                interval=CONF.trigger_poll_interval,
                stop_on_exception=False,
            )

        self._register()

    def _register(self):
        self.__class__._triggers[self._id] = self

    def _unregister(self):
        del self.__class__._triggers[self._id]

    @classmethod
    def _loop(cls):
        while True:
            now = datetime.utcnow()
            exec_to_handle = cls._trigger_execution_get_next()
            if not exec_to_handle:
                LOG.debug("No next trigger executions")
                break

            trigger_id = exec_to_handle.trigger_id
            execution_time = exec_to_handle.execution_time
            trigger = cls._triggers.get(trigger_id)
            if not trigger:
                LOG.warning("Unable to find trigger %s", trigger_id)
                res = cls._trigger_execution_delete(
                    execution_id=exec_to_handle.id)
                continue

            if now < execution_time:
                LOG.debug("Time trigger not yet due")
                break

            trigger_property = trigger._trigger_property
            timer = cls._get_timer(trigger_property)
            window = trigger_property.get("window")
            end_time_to_run = execution_time + timedelta(
                seconds=window)

            if now > end_time_to_run:
                LOG.debug("Time trigger (%s) out of window",)
                execute = False
            else:
                LOG.debug("Time trigger (%s) is due", trigger_id)
                execute = True

            next_exec_time = cls._compute_next_run_time(
                now,
                trigger_property['end_time'],
                timer,
            )
            if not next_exec_time:
                LOG.debug("No more planned executions for trigger (%s)",
                          trigger_id)
                res = cls._trigger_execution_delete(
                    execution_id=exec_to_handle.id)
            else:
                LOG.debug("Rescheduling (%s) from %s to %s",
                          trigger_id,
                          execution_time,
                          next_exec_time)
                res = cls._trigger_execution_update(
                    exec_to_handle.id,
                    execution_time,
                    next_exec_time,
                )

            if not res:
                LOG.info("Trigger probably handled by another node")
                continue

            if execute:
                cls._trigger_operations(trigger_id, execution_time, window)

    @classmethod
    def _trigger_execution_new(cls, trigger_id, time):
        # Find the first time.
        # We don't known when using this trigger first time.
        ctxt = karbor_context.get_admin_context()
        try:
            db.trigger_execution_create(ctxt, trigger_id, time)
            return True
        except Exception:
            return False

    @classmethod
    def _trigger_execution_update(cls, id, current_time, next_time):
        ctxt = karbor_context.get_admin_context()
        return db.trigger_execution_update(ctxt, id, current_time, next_time)

    @classmethod
    def _trigger_execution_delete(cls, execution_id=None, trigger_id=None):
        if execution_id is None and trigger_id is None:
            raise exception.InvalidParameterValue('supply at least one id')

        ctxt = karbor_context.get_admin_context()
        num_deleted = db.trigger_execution_delete(ctxt, execution_id,
                                                  trigger_id)
        return num_deleted > 0

    @classmethod
    def _trigger_execution_get_next(cls):
        ctxt = karbor_context.get_admin_context()
        return db.trigger_execution_get_next(ctxt)

    def shutdown(self):
        self._unregister()

    def register_operation(self, operation_id, **kwargs):
        if operation_id in self._operation_ids:
            msg = (_("The operation_id(%s) is exist") % operation_id)
            raise exception.ScheduledOperationExist(msg)

        self._operation_ids.add(operation_id)

    def unregister_operation(self, operation_id, **kwargs):
        self._operation_ids.discard(operation_id)

    def update_trigger_property(self, trigger_property):
        valid_trigger_property = self.check_trigger_definition(
            trigger_property)

        if valid_trigger_property == self._trigger_property:
            return

        timer = self._get_timer(valid_trigger_property)
        first_run_time = self._compute_next_run_time(
            datetime.utcnow(), valid_trigger_property['end_time'], timer)

        if not first_run_time:
            msg = (_("The new trigger property is invalid, "
                     "Can not find the first run time"))
            raise exception.InvalidInput(msg)

        self._trigger_property = valid_trigger_property
        self._trigger_execution_delete(trigger_id=self._id)
        self._trigger_execution_new(self._id, first_run_time)

    @classmethod
    def _trigger_operations(cls, trigger_id, expect_run_time, window):
        """Trigger operations once"""

        # The executor execute_operation may have I/O operation.
        # If it is, this green thread will be switched out during looping
        # operation_ids. In order to avoid changing self._operation_ids
        # during the green thread is switched out, copy self._operation_ids
        # as the iterative object.
        trigger = cls._triggers.get(trigger_id)
        if not trigger:
            LOG.warning("Can't find trigger: %s" % trigger_id)
            return
        operations_ids = trigger._operation_ids.copy()
        sent_ops = set()
        end_time = expect_run_time + timedelta(seconds=window)

        for operation_id in operations_ids:
            if operation_id not in trigger._operation_ids:
                # Maybe, when traversing this operation_id, it has been
                # removed by self.unregister_operation
                LOG.warning("Execute operation %s which is not exist, "
                            "ignore it", operation_id)
                continue

            now = datetime.utcnow()
            if now >= end_time:
                LOG.error("Can not trigger operations to run. Because it is "
                          "out of window time. now=%(now)s, "
                          "end time=%(end_time)s, waiting operations=%(ops)s",
                          {'now': now, 'end_time': end_time,
                           'ops': operations_ids - sent_ops})
                break

            try:
                trigger._executor.execute_operation(
                    operation_id, now, expect_run_time, window)
            except Exception:
                LOG.exception("Submit operation to executor failed, operation"
                              " id=%s", operation_id)

            sent_ops.add(operation_id)

    @classmethod
    def check_trigger_definition(cls, trigger_definition):
        return utils.check_trigger_definition(trigger_definition)

    @classmethod
    def _compute_next_run_time(cls, start_time, end_time, timer):
        return utils.compute_next_run_time(start_time, end_time, timer)

    @classmethod
    def _get_timer(cls, trigger_property):
        return utils.get_timer(trigger_property)

    @classmethod
    def check_configuration(cls):
        utils.check_configuration()
