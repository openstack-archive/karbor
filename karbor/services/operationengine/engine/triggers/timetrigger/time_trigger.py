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
import functools

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils

from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine import triggers
from karbor.services.operationengine.engine.triggers.timetrigger import utils

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class TriggerOperationGreenThread(object):
    def __init__(self, first_run_time, function):
        super(TriggerOperationGreenThread, self).__init__()
        self._is_sleeping = True
        self._pre_run_time = None
        self._running = False
        self._thread = None

        self._function = function

        self._start(first_run_time)

    def kill(self):
        self._running = False
        if self._is_sleeping:
            self._thread.kill()

    @property
    def running(self):
        return self._running

    @property
    def pre_run_time(self):
        return self._pre_run_time

    def _start(self, first_run_time):
        self._running = True

        now = datetime.utcnow()
        initial_delay = 0 if first_run_time <= now else (
            int(timeutils.delta_seconds(now, first_run_time)))

        self._thread = eventlet.spawn_after(
            initial_delay, self._run, first_run_time)
        self._thread.link(self._on_done)

    def _on_done(self, gt, *args, **kwargs):
        self._is_sleeping = True
        self._pre_run_time = None
        self._running = False
        self._thread = None

    def _run(self, expect_run_time):
        while self._running:
            self._is_sleeping = False
            self._pre_run_time = expect_run_time

            expect_run_time = self._function(expect_run_time)
            if expect_run_time is None or not self._running:
                break

            self._is_sleeping = True

            now = datetime.utcnow()
            idle_time = 0 if expect_run_time <= now else int(
                timeutils.delta_seconds(now, expect_run_time))
            eventlet.sleep(idle_time)


class TimeTrigger(triggers.BaseTrigger):
    TRIGGER_TYPE = "time"
    IS_ENABLED = (CONF.scheduling_strategy == 'default')

    def __init__(self, trigger_id, trigger_property, executor):
        super(TimeTrigger, self).__init__(
            trigger_id, trigger_property, executor)

        self._trigger_property = self.check_trigger_definition(
            trigger_property)

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

        timer = self._get_timer(valid_trigger_property)
        first_run_time = self._compute_next_run_time(
            datetime.utcnow(), trigger_property['end_time'], timer)
        if not first_run_time:
            msg = (_("The new trigger property is invalid, "
                     "Can not find the first run time"))
            raise exception.InvalidInput(msg)

        if self._greenthread is not None:
            pre_run_time = self._greenthread.pre_run_time
            if pre_run_time:
                end_time = pre_run_time + timedelta(
                    seconds=self._trigger_property['window'])
                if first_run_time <= end_time:
                    msg = (_("The new trigger property is invalid, "
                             "First run time%(t1)s must be after %(t2)s") %
                           {'t1': first_run_time, 't2': end_time})
                    raise exception.InvalidInput(msg)

        self._trigger_property = valid_trigger_property

        if len(self._operation_ids) > 0:
            # Restart greenthread to take the change of trigger property
            # effect immediately
            self._kill_greenthread()
            self._create_green_thread(first_run_time, timer)

    def _kill_greenthread(self):
        if self._greenthread:
            self._greenthread.kill()
            self._greenthread = None

    def _start_greenthread(self):
        # Find the first time.
        # We don't known when using this trigger first time.
        timer = self._get_timer(self._trigger_property)
        first_run_time = self._compute_next_run_time(
            datetime.utcnow(), self._trigger_property['end_time'], timer)
        if not first_run_time:
            raise exception.TriggerIsInvalid(trigger_id=self._id)

        self._create_green_thread(first_run_time, timer)

    def _create_green_thread(self, first_run_time, timer):
        func = functools.partial(
            self._trigger_operations,
            trigger_property=self._trigger_property.copy(),
            timer=timer)

        self._greenthread = TriggerOperationGreenThread(
            first_run_time, func)

    def _trigger_operations(self, expect_run_time, trigger_property, timer):
        """Trigger operations once

        returns: wait time for next run
        """

        # Just for robustness, actually expect_run_time always <= now
        # but, if the scheduling of eventlet is not accurate, then we
        # can do some adjustments.
        entry_time = datetime.utcnow()
        if entry_time < expect_run_time and (
                int(timeutils.delta_seconds(entry_time, expect_run_time)) > 0):
            return expect_run_time

        # The self._executor.execute_operation may have I/O operation.
        # If it is, this green thread will be switched out during looping
        # operation_ids. In order to avoid changing self._operation_ids
        # during the green thread is switched out, copy self._operation_ids
        # as the iterative object.
        operation_ids = self._operation_ids.copy()
        sent_ops = set()
        window = trigger_property.get("window")
        end_time = expect_run_time + timedelta(seconds=window)

        for operation_id in operation_ids:
            if operation_id not in self._operation_ids:
                # Maybe, when traversing this operation_id, it has been
                # removed by self.unregister_operation
                LOG.warning("Execute operation %s which is not exist, "
                            "ignore it", operation_id)
                continue

            now = datetime.utcnow()
            if now >= end_time:
                LOG.error("Can not trigger operations to run. Because it is "
                          "out of window time. now=%(now)s, "
                          "end time=%(end_time)s, expect run time=%(expect)s,"
                          " wating operations=%(ops)s",
                          {'now': now, 'end_time': end_time,
                           'expect': expect_run_time,
                           'ops': operation_ids - sent_ops})
                break

            try:
                self._executor.execute_operation(
                    operation_id, now, expect_run_time, window)
            except Exception:
                LOG.exception("Submit operation to executor failed, operation"
                              " id=%s", operation_id)

            sent_ops.add(operation_id)

        next_time = self._compute_next_run_time(
            expect_run_time, trigger_property['end_time'], timer)
        now = datetime.utcnow()
        if next_time and next_time <= now:
            LOG.error("Next run time:%(next_time)s <= now:%(now)s. Maybe the "
                      "entry time=%(entry)s is too late, even exceeds the end"
                      " time of window=%(end)s, or it was blocked where "
                      "sending the operation to executor.",
                      {'next_time': next_time, 'now': now,
                       'entry': entry_time, 'end': end_time})
        return next_time

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
