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

from karbor import exception
from karbor.services.operationengine.engine.triggers.timetrigger.time_trigger \
    import TimeTrigger
from karbor.tests import base


class FakeExecutor(object):
    def __init__(self):
        self._ops = {}

    def execute_operation(self, operation_id, triggered_time,
                          expect_start_time, window):

        if operation_id not in self._ops:
            self._ops[operation_id] = 0
        self._ops[operation_id] += 1


class TimeTriggerTestCase(base.TestCase):

    def setUp(self):
        super(TimeTriggerTestCase, self).setUp()

        self.override_config('min_interval', 60)
        trigger_property = {
            "format": "crontab",
            "pattern": "* * * * *",
            "window": 10,
            "start_time": datetime.utcnow() + timedelta(seconds=1),
            "end_time": datetime.utcnow()
        }
        self._trigger = TimeTrigger("123", trigger_property, FakeExecutor())

    def tearDown(self):
        super(TimeTriggerTestCase, self).tearDown()

        self._trigger.shutdown()

    def test_check_trigger_property_window(self):
        trigger_property = {
            "format": "crontab",
            "pattern": "* * * * *",
            "window": "abc"
        }

        self.assertRaisesRegexp(exception.InvalidInput,
                                "The trigger window.* is not integer",
                                TimeTrigger.check_trigger_definition,
                                trigger_property)

    def test_check_trigger_property_start_time(self):
        trigger_property = {
            "format": "crontab",
            "pattern": "* * * * *",
            "window": 10,
            "start_time": "abc"
        }

        self.assertRaisesRegexp(exception.InvalidInput,
                                "The format of trigger .* is not correct",
                                TimeTrigger.check_trigger_definition,
                                trigger_property)

    def test_check_trigger_property_end_time(self):
        trigger_property = {
            "format": "crontab",
            "pattern": "* * * * *",
            "window": 10,
            "end_time": "abc"
        }

        self.assertRaisesRegexp(exception.InvalidInput,
                                "The format of trigger .* is not correct",
                                TimeTrigger.check_trigger_definition,
                                trigger_property)

    def test_register_operation(self):
        operation_id = "1"
        self._register_operation(operation_id)

        self.assertRaisesRegexp(exception.ScheduledOperationExist,
                                "The operation_id.* is exist",
                                self._trigger.register_operation,
                                operation_id)

        self.assertRaises(exception.TriggerIsInvalid,
                          self._trigger.register_operation,
                          "2")

    def test_unregister_operation(self):
        operation_id = "2"
        self._register_operation(operation_id)

        self.assertIn(operation_id, self._trigger._operation_ids)
        self._trigger.unregister_operation(operation_id)
        self.assertNotIn(operation_id, self._trigger._operation_ids)

    def test_update_trigger_property(self):
        operation_id = "3"
        self._register_operation(operation_id)

        trigger_property = {
            "format": "crontab",
            "pattern": "* * * * *",
            "window": 10,
            "start_time": datetime.utcnow() + timedelta(seconds=1),
            "end_time": datetime.utcnow()
        }

        self._trigger.update_trigger_property(trigger_property)
        eventlet.sleep(1)
        self.assertEqual(2, self._trigger._executor._ops[operation_id])

    def _register_operation(self, operation_id):
        self._trigger.register_operation(operation_id)
        eventlet.sleep(1)
        self.assertEqual(1, self._trigger._executor._ops[operation_id])
