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
import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
import six

from karbor import exception
from karbor.i18n import _, _LE
from karbor.services.operationengine.engine import triggers
from karbor.services.operationengine.engine.triggers.timetrigger import\
    time_format_manager

time_trigger_opts = [
    cfg.IntOpt('min_interval',
               default=60 * 60,
               help='The interval of two adjacent time points'),

    cfg.IntOpt('window_time',
               default=60,
               help='The default window time'),
    ]

CONF = cfg.CONF
CONF.register_opts(time_trigger_opts)
LOG = logging.getLogger(__name__)


class TriggerOperationGreenThread(object):
    def __init__(self, first_run_time, function):

        self._running = False
        self._thread = None
        self._function = function

        self._start(first_run_time)

    def kill(self):
        self._running = False

    @property
    def running(self):
        return self._running

    def _on_done(self, gt, *args, **kwargs):
        self._thread = None
        self._running = False

    def _start(self, first_run_time):
        self._running = True

        now = datetime.utcnow()
        initial_delay = 0 if first_run_time <= now else (
            int(timeutils.delta_seconds(now, first_run_time)))

        self._thread = eventlet.spawn_after(initial_delay, self._run)
        self._thread.link(self._on_done)

    def _run(self):
        while self._running:
            idle_time = self._function()
            if idle_time is None:
                break
            eventlet.sleep(idle_time)


class TimeTrigger(triggers.BaseTrigger):
    TRIGGER_TYPE = "time"

    TIME_FORMAT_MANAGER = time_format_manager.TimeFormatManager()

    def __init__(self, trigger_id, trigger_property, executor):
        super(TimeTrigger, self).__init__(trigger_id, executor)

        self._trigger_property = self.check_trigger_definition(
            trigger_property)
        self._window = int(
            trigger_property.get("window", CONF.window_time))

        # Only when creating trigger, if user doesn't specify the start_time
        # then the next run time = now
        now = datetime.utcnow()
        start_time = self._trigger_property["start_time"]
        self._next_run_time = now if not start_time else start_time
        self._greenthread = None

    def shutdown(self):
        self._kill_greenthread()

    def register_operation(self, operation_id, **kwargs):
        if operation_id in self._operation_ids:
            msg = (_("The operation_id(%s) is exist") % operation_id)
            raise exception.ScheduledOperationExist(msg)

        if self._greenthread and not self._greenthread.running:
            raise exception.TriggerIsInvalid(trigger_id=self._id)

        self._operation_ids.add(operation_id)
        if self._greenthread is None:
            self._start_greenthread()

    def unregister_operation(self, operation_id, **kwargs):
        if operation_id not in self._operation_ids:
            return

        self._operation_ids.remove(operation_id)
        if 0 == len(self._operation_ids):
            self._kill_greenthread()

    def update_trigger_property(self, trigger_property):
        valid_trigger_property = self.check_trigger_definition(
            trigger_property)

        if valid_trigger_property == self._trigger_property:
            return

        start_time = valid_trigger_property["start_time"]
        if self._next_run_time is None and start_time is None:
            msg = (_("The start_time should not be None"))
            raise exception.InvalidInput(msg)
        if start_time:
            self._next_run_time = start_time

        self._window = int(
            valid_trigger_property.get('window', self._window))

        self._trigger_property.update(valid_trigger_property)

        if len(self._operation_ids) > 0:
            # Restart greenthread to take the change of trigger property
            # effect immediately
            self._restart_greenthread()

    def _kill_greenthread(self):
        if self._greenthread:
            self._greenthread.kill()
            self._greenthread = None

    def _restart_greenthread(self):
        self._kill_greenthread()
        self._start_greenthread()

    def _start_greenthread(self):
        if not self._next_run_time:
            raise exception.TriggerIsInvalid(trigger_id=self._id)

        now = datetime.utcnow()
        first_run_time = self._next_run_time
        if first_run_time < now:
            # Find the first time. We don't known when first use this trigger.
            tmp_time = now - timedelta(seconds=self._window)
            if tmp_time < first_run_time:
                tmp_time = first_run_time
            first_run_time = self._compute_next_run_time(
                tmp_time,
                self._trigger_property['end_time'],
                self._trigger_property['format'],
                self._trigger_property['pattern'])

            if not first_run_time:
                raise exception.TriggerIsInvalid(trigger_id=self._id)

            self._next_run_time = first_run_time

        self._greenthread = TriggerOperationGreenThread(
            first_run_time, self._trigger_operations)

    def _trigger_operations(self):
        """Trigger operations once

        returns: wait time for next run
        """
        now = datetime.utcnow()
        expect_run_time = self._next_run_time
        # Just for robustness, actually expect_run_time always <= now
        # but, if the scheduling of eventlet is not accurate, then we
        # can do some adjustments.
        if expect_run_time > now:
            return int(timeutils.delta_seconds(now, expect_run_time))

        window = self._window
        if now > (expect_run_time + timedelta(seconds=window)):
            LOG.exception(_LE("TimeTrigger didn't trigger operation "
                              "on time, now=%(now)s, expect_run_time="
                              "%(expect_run_time)s, window=%(window)d"),
                          {'now': now,
                           'expect_run_time': expect_run_time,
                           'window': window})
        else:
            # The self._executor.execute_operation may have I/O operation.
            # If it is, this green thread will be switched out during looping
            # operation_ids. In order to avoid changing self._operation_ids
            # during the green thread is switched out, copy self._operation_ids
            # as the iterative object.
            operation_ids = self._operation_ids.copy()
            for operation_id in operation_ids:
                try:
                    self._executor.execute_operation(
                        operation_id, now, expect_run_time, window)
                except Exception:
                    LOG.exception(_LE("Submit operation to executor "
                                      "failed, id=%(op_id)s"),
                                  operation_id)
                    pass

        self._next_run_time = self._compute_next_run_time(
            datetime.utcnow(), self._trigger_property['end_time'],
            self._trigger_property['format'],
            self._trigger_property['pattern'])

        return None if not self._next_run_time else (int(
            timeutils.delta_seconds(now, self._next_run_time)))

    @classmethod
    def check_trigger_definition(cls, trigger_definition):
        """Check trigger definition

        All the time instances of trigger_definition are in UTC,
        including start_time, end_time
        """

        trigger_format = trigger_definition.get("format", None)
        pattern = trigger_definition.get("pattern", None)
        cls.TIME_FORMAT_MANAGER.check_time_format(
            trigger_format, pattern)

        interval = int(cls.TIME_FORMAT_MANAGER.get_interval(
            trigger_format, pattern))
        if interval < CONF.min_interval:
            msg = (_("The interval of two adjacent time points "
                     "is less than %d") % CONF.min_interval)
            raise exception.InvalidInput(msg)

        window = trigger_definition.get("window", CONF.window_time)
        if not isinstance(window, int):
            try:
                window = int(window)
            except Exception:
                msg = (_("The trigger windows(%s) is not integer") % window)
                raise exception.InvalidInput(msg)
        if window <= 0:
            msg = (_("The trigger windows(%d) must be positive") % window)
            raise exception.InvalidInput(msg)
        if (window * 2) > interval:
            msg = (_("The trigger windows%(window)d must be less "
                     "than %(interval)d") % {"window": window,
                                             "interval": interval / 2})
            raise exception.InvalidInput(msg)

        end_time = trigger_definition.get("end_time", None)
        end_time = cls._check_and_get_datetime(end_time, "end_time")

        start_time = trigger_definition.get("start_time", None)
        start_time = cls._check_and_get_datetime(start_time, "start_time")

        valid_trigger_property = trigger_definition.copy()
        valid_trigger_property['start_time'] = start_time
        valid_trigger_property['end_time'] = end_time
        return valid_trigger_property

    @classmethod
    def _check_and_get_datetime(cls, time, time_name):
        if not time or isinstance(time, datetime):
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
    def _compute_next_run_time(cls, start_time, end_time,
                               trigger_format, trigger_pattern):

        next_time = cls.TIME_FORMAT_MANAGER.compute_next_time(
            trigger_format, trigger_pattern, start_time)

        if next_time and (not end_time or next_time <= end_time):
            return next_time
        return None
