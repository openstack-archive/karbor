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
import mock
from oslo_config import cfg

from karbor import exception
from karbor.services.operationengine.engine.triggers.timetrigger.time_trigger \
    import TimeTrigger
from karbor.tests import base


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

    def clear(self):
        self._ops.clear()


class TimeTriggerTestCase(base.TestCase):

    def setUp(self):
        super(TimeTriggerTestCase, self).setUp()

        self._set_configuration()

        mock_obj = mock.Mock()
        mock_obj.return_value = FakeTimeFormat
        TimeTrigger._get_time_format_class = mock_obj

        self._default_executor = FakeExecutor()

    def test_check_configuration(self):
        self._set_configuration(10, 20, 30)
        self.assertRaisesRegex(exception.InvalidInput,
                               "Configurations of time trigger are invalid",
                               TimeTrigger.check_configuration)
        self._set_configuration()

    def test_check_trigger_property_start_time(self):
        trigger_property = {
            "pattern": "",
            "start_time": ""
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger\'s start time is unknown",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

        trigger_property['start_time'] = 'abc'
        self.assertRaisesRegex(exception.InvalidInput,
                               "The format of trigger .* is not correct",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

        trigger_property['start_time'] = 123
        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger .* is not an instance of string",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

    @mock.patch.object(FakeTimeFormat, 'get_min_interval')
    def test_check_trigger_property_interval(self, get_min_interval):
        get_min_interval.return_value = 0

        trigger_property = {
            "start_time": '2016-8-18 01:03:04'
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The interval of two adjacent time points .*",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

    def test_check_trigger_property_window(self):
        trigger_property = {
            "window": "abc",
            "start_time": '2016-8-18 01:03:04'
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger window.* is not integer",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

        trigger_property['window'] = 1000
        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger windows .* must be between .*",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

    def test_check_trigger_property_end_time(self):
        trigger_property = {
            "window": 15,
            "start_time": '2016-8-18 01:03:04',
            "end_time": "abc"
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               "The format of trigger .* is not correct",
                               TimeTrigger.check_trigger_definition,
                               trigger_property)

    def test_register_operation(self):
        trigger = self._generate_trigger()

        operation_id = "1"
        trigger.register_operation(operation_id)
        eventlet.sleep(0.3)

        self.assertGreaterEqual(trigger._executor._ops[operation_id], 1)
        self.assertRaisesRegex(exception.ScheduledOperationExist,
                               "The operation_id.* is exist",
                               trigger.register_operation,
                               operation_id)

        eventlet.sleep(0.3)
        self.assertRaises(exception.TriggerIsInvalid,
                          trigger.register_operation,
                          "2")

    def test_unregister_operation(self):
        trigger = self._generate_trigger()
        operation_id = "2"

        trigger.register_operation(operation_id)
        self.assertIn(operation_id, trigger._operation_ids)

        trigger.unregister_operation(operation_id)
        self.assertNotIn(operation_id, trigger._operation_ids)

    def test_unregister_operation_when_scheduling(self):
        trigger = self._generate_trigger()

        for op_id in ['1', '2', '3']:
            trigger.register_operation(op_id)
            self.assertIn(op_id, trigger._operation_ids)
        eventlet.sleep(0.5)

        for op_id in ['2', '3']:
            trigger.unregister_operation(op_id)
            self.assertNotIn(op_id, trigger._operation_ids)
        eventlet.sleep(0.6)

        self.assertGreaterEqual(trigger._executor._ops['1'], 1)

        self.assertTrue(('2' not in trigger._executor._ops) or (
            '3' not in trigger._executor._ops))

    def test_update_trigger_property(self):
        trigger = self._generate_trigger()

        trigger_property = {
            "pattern": "",
            "window": 15,
            "start_time": datetime.utcnow(),
            "end_time": datetime.utcnow()
        }

        self.assertRaisesRegex(exception.InvalidInput,
                               ".*Can not find the first run tim",
                               trigger.update_trigger_property,
                               trigger_property)

        trigger.register_operation('1')
        eventlet.sleep(0.2)
        trigger_property['end_time'] = (
            datetime.utcnow() + timedelta(seconds=1))
        self.assertRaisesRegex(exception.InvalidInput,
                               ".*First run time.* must be after.*",
                               trigger.update_trigger_property,
                               trigger_property)

    def test_update_trigger_property_success(self):
        trigger = self._generate_trigger()
        trigger.register_operation('1')
        eventlet.sleep(0.2)

        trigger_property = {
            "pattern": "",
            "window": 15,
            "start_time": datetime.utcnow(),
            "end_time": ''
        }
        with mock.patch.object(FakeTimeFormat, 'compute_next_time') as c:
            c.return_value = datetime.utcnow() + timedelta(seconds=20)
            old_id = id(trigger._greenthread)

            trigger.update_trigger_property(trigger_property)

            self.assertNotEqual(old_id, id(trigger._greenthread))

    def _generate_trigger(self, end_time=None):
        if not end_time:
            end_time = datetime.utcnow() + timedelta(seconds=1)

        trigger_property = {
            "pattern": "",
            "window": 15,
            "start_time": datetime.utcnow(),
            "end_time": end_time
        }

        self._default_executor.clear()
        return TimeTrigger("123", trigger_property, self._default_executor)

    def _set_configuration(self, min_window=15,
                           max_window=30, min_interval=60):
        self.override_config('min_interval', min_interval)
        self.override_config('min_window_time', min_window)
        self.override_config('max_window_time', max_window)
