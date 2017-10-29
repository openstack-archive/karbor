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
from oslo_utils import timeutils
import six
from stevedore import driver as import_driver

from karbor import context as karbor_context
from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine import triggers

time_trigger_opts = [
    cfg.IntOpt('min_interval',
               default=60 * 60,
               help='The minimum interval of two adjacent time points. '
                    'min_interval >= (max_window_time * 2)'),

    cfg.IntOpt('min_window_time',
               default=900,
               help='The minimum window time'),

    cfg.IntOpt('max_window_time',
               default=1800,
               help='The maximum window time'),

    cfg.IntOpt('trigger_poll_interval',
               default=15,
               help='Interval, in seconds, in which Karbor will poll for '
                    'trigger events'),
]

CONF = cfg.CONF
CONF.register_opts(time_trigger_opts)
LOG = logging.getLogger(__name__)


class TimeTrigger(triggers.BaseTrigger):
    TRIGGER_TYPE = "time"
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
            res = False
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
        """Check trigger definition

        All the time instances of trigger_definition are in UTC,
        including start_time, end_time
        """
        tf_cls = cls._get_time_format_class()

        pattern = trigger_definition.get("pattern", None)
        tf_cls.check_time_format(pattern)

        start_time = trigger_definition.get("start_time", None)
        if not start_time:
            msg = _("The trigger\'s start time is unknown")
            raise exception.InvalidInput(msg)
        start_time = cls._check_and_get_datetime(start_time, "start_time")

        interval = tf_cls(start_time, pattern).get_min_interval()
        if interval is not None and interval < CONF.min_interval:
            msg = (_("The interval of two adjacent time points "
                     "is less than %d") % CONF.min_interval)
            raise exception.InvalidInput(msg)

        window = trigger_definition.get("window", CONF.min_window_time)
        if not isinstance(window, int):
            try:
                window = int(window)
            except Exception:
                msg = (_("The trigger windows(%s) is not integer") % window)
                raise exception.InvalidInput(msg)

        if window < CONF.min_window_time or window > CONF.max_window_time:
            msg = (_("The trigger windows %(window)d must be between "
                     "%(min_window)d and %(max_window)d") %
                   {"window": window,
                    "min_window": CONF.min_window_time,
                    "max_window": CONF.max_window_time})
            raise exception.InvalidInput(msg)

        end_time = trigger_definition.get("end_time", None)
        end_time = cls._check_and_get_datetime(end_time, "end_time")

        valid_trigger_property = trigger_definition.copy()
        valid_trigger_property['window'] = window
        valid_trigger_property['start_time'] = start_time
        valid_trigger_property['end_time'] = end_time
        return valid_trigger_property

    @classmethod
    def _check_and_get_datetime(cls, time, time_name):
        if not time:
            return None

        if isinstance(time, datetime):
            return time

        if not isinstance(time, six.string_types):
            msg = (_("The trigger %(name)s(type = %(vtype)s) is not an "
                     "instance of string") %
                   {"name": time_name, "vtype": type(time)})
            raise exception.InvalidInput(msg)

        try:
            time = timeutils.parse_strtime(time, fmt='%Y-%m-%d %H:%M:%S')
        except Exception:
            msg = (_("The format of trigger %s is not correct") % time_name)
            raise exception.InvalidInput(msg)

        return time

    @classmethod
    def _compute_next_run_time(cls, start_time, end_time, timer):
        next_time = timer.compute_next_time(start_time)

        if next_time and (not end_time or next_time <= end_time):
            return next_time
        return None

    @classmethod
    def _get_time_format_class(cls):
        return import_driver.DriverManager(
            'karbor.operationengine.engine.timetrigger.time_format',
            CONF.time_format).driver

    @classmethod
    def _get_timer(cls, trigger_property):
        tf_cls = cls._get_time_format_class()
        timer = tf_cls(trigger_property['start_time'],
                       trigger_property['pattern'])
        return timer

    @classmethod
    def check_configuration(cls):
        min_window = CONF.min_window_time
        max_window = CONF.max_window_time
        min_interval = CONF.min_interval

        if not (min_window < max_window and (max_window * 2 <= min_interval)):
            msg = (_('Configurations of time trigger are invalid'))
            raise exception.InvalidInput(msg)
