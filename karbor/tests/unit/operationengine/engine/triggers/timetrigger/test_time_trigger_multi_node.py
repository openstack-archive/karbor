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

from collections import namedtuple
from datetime import datetime
from datetime import timedelta
import eventlet
import functools
import heapq
import mock
from oslo_config import cfg
from oslo_utils import uuidutils

from karbor import context as karbor_context
from karbor import exception
from karbor.services.operationengine.engine.triggers.timetrigger import \
    time_trigger_multi_node as tt
from karbor.services.operationengine.engine.triggers.timetrigger import utils
from karbor.tests import base


TriggerExecution = namedtuple('TriggerExecution',
                              ['execution_time', 'id', 'trigger_id'])


class FakeTimeFormat(object):
    def __init__(self, start_time, pattern):
        super(FakeTimeFormat, self).__init__()

    @classmethod
    def check_time_format(cls, pattern):
        pass

    def compute_next_time(self, current_time):
        return current_time + timedelta(seconds=0.5)

    def get_min_interval(self):
        return cfg.CONF.min_interval


class FakeExecutor(object):
    def __init__(self):
        super(FakeExecutor, self).__init__()
        self._ops = {}

    def execute_operation(self, operation_id, triggered_time,
                          expect_start_time, window):
        if operation_id not in self._ops:
            self._ops[operation_id] = 0
        self._ops[operation_id] += 1
        eventlet.sleep(0.5)


class FakeTimeTrigger(object):
    @classmethod
    def get_time_format(cls, *args, **kwargs):
        return FakeTimeFormat


class FakeDb(object):
    def __init__(self):
        self._db = []

    def trigger_execution_get_next(self, context):
        if len(self._db) == 0:
            return None
        return self._db[0]

    def trigger_execution_create(self, context, trigger_id, time):
        element = TriggerExecution(time, uuidutils.generate_uuid(), trigger_id)
        heapq.heappush(self._db, element)

    def trigger_execution_update(self, context, id, current_time, new_time):
        for idx, element in enumerate(self._db):
            if element.id == id:
                if element.execution_time != current_time:
                    return False
                self._db[idx] = TriggerExecution(new_time, element.id,
                                                 element.trigger_id)
                break
        heapq.heapify(self._db)
        return True

    def trigger_execution_delete(self, context, id, trigger_id):
        removed_ids = []
        for idx, element in enumerate(self._db):
            if (id and element.id == id) or (trigger_id and
                                             element.trigger_id == trigger_id):
                removed_ids.append(idx)

        for idx in reversed(removed_ids):
            self._db.pop(idx)
        heapq.heapify(self._db)
        return len(removed_ids)


def time_trigger_test(func):
    @functools.wraps(func)
    @mock.patch.object(tt, 'db', FakeDb())
    @mock.patch.object(karbor_context, 'get_admin_context', lambda: None)
    @mock.patch.object(utils, 'get_time_format_class',
                       FakeTimeTrigger.get_time_format)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


class TimeTriggerTestCase(base.TestCase):
    _tid = 0
    _default_executor = FakeExecutor()

    def setUp(self):
        super(TimeTriggerTestCase, self).setUp()
        self._set_configuration()

    def test_check_configuration(self):
        self._set_configuration(10, 20, 30)
        self.assertRaisesRegex(exception.InvalidInput,
                               "Configurations of time trigger are invalid",
                               tt.TimeTrigger.check_configuration)
        self._set_configuration()

    @time_trigger_test
    def test_check_trigger_property_start_time(self):
        trigger_property = {
            "pattern": "",
            "start_time": ""
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger\'s start time is unknown",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

        trigger_property['start_time'] = 'abc'
        self.assertRaisesRegex(exception.InvalidInput,
                               "The format of trigger .* is not correct",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

        trigger_property['start_time'] = 123
        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger .* is not an instance of string",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

    @mock.patch.object(FakeTimeFormat, 'get_min_interval')
    @time_trigger_test
    def test_check_trigger_property_interval(self, get_min_interval):
        get_min_interval.return_value = 0

        trigger_property = {
            "start_time": '2016-8-18 01:03:04'
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The interval of two adjacent time points .*",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

    @time_trigger_test
    def test_check_trigger_property_window(self):
        trigger_property = {
            "window": "abc",
            "start_time": '2016-8-18 01:03:04'
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger window.* is not integer",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

        trigger_property['window'] = 1000
        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger windows .* must be between .*",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

    @time_trigger_test
    def test_check_trigger_property_end_time(self):
        trigger_property = {
            "window": 15,
            "start_time": '2016-8-18 01:03:04',
            "end_time": "abc"
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The format of trigger .* is not correct",
                               tt.TimeTrigger.check_trigger_definition,
                               trigger_property)

    @time_trigger_test
    def test_register_operation(self):
        trigger = self._generate_trigger()

        operation_id = "1"
        trigger.register_operation(operation_id)
        eventlet.sleep(2)

        self.assertGreaterEqual(self._default_executor._ops[operation_id], 1)
        self.assertRaisesRegex(exception.ScheduledOperationExist,
                               "The operation_id.* is exist",
                               trigger.register_operation,
                               operation_id)

    @time_trigger_test
    def test_unregister_operation(self):
        trigger = self._generate_trigger()
        operation_id = "2"

        trigger.register_operation(operation_id)
        self.assertIn(operation_id, trigger._operation_ids)

        trigger.unregister_operation(operation_id)
        self.assertNotIn(trigger._id, trigger._operation_ids)

    @time_trigger_test
    def test_update_trigger_property(self):
        trigger = self._generate_trigger()

        trigger_property = {
            "pattern": "",
            "window": 15,
            "start_time": '2016-8-18 01:03:04',
            "end_time": datetime.utcnow(),
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               ".*Can not find the first run time",
                               trigger.update_trigger_property,
                               trigger_property)

    @time_trigger_test
    def test_update_trigger_property_success(self):
        trigger = self._generate_trigger()
        trigger.register_operation('7')
        eventlet.sleep(0.2)

        trigger_property = {
            "pattern": "",
            "window": 15,
            "start_time": datetime.utcnow(),
            "end_time": ''
        }
        with mock.patch.object(FakeTimeFormat, 'compute_next_time') as c:
            c.return_value = datetime.utcnow() + timedelta(seconds=20)
            trigger.update_trigger_property(trigger_property)

    def _generate_trigger(self, end_time=None):
        if not end_time:
            end_time = datetime.utcnow() + timedelta(seconds=1)

        trigger_property = {
            "pattern": "",
            "window": 15,
            "start_time": datetime.utcnow(),
            "end_time": end_time
        }

        return tt.TimeTrigger(
            uuidutils.generate_uuid(),
            trigger_property,
            self._default_executor,
        )

    def _set_configuration(self, min_window=15,
                           max_window=30, min_interval=60, poll_interval=1):
        self.override_config('min_interval', min_interval)
        self.override_config('min_window_time', min_window)
        self.override_config('max_window_time', max_window)
        self.override_config('trigger_poll_interval', poll_interval)
