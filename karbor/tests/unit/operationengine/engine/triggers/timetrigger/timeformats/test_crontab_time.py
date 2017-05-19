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

from karbor import exception
from karbor.services.operationengine.engine.triggers.timetrigger.timeformats \
    import crontab_time
from karbor.tests import base


class CrontabTimeTestCase(base.TestCase):

    def setUp(self):
        super(CrontabTimeTestCase, self).setUp()

        self._time_format = crontab_time.Crontab

    def test_none_pattern(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger pattern is None",
                               self._time_format.check_time_format,
                               "")

    def test_invalid_pattern(self):
        self.assertRaisesRegex(exception.InvalidInput,
                               "The trigger pattern.* is invalid",
                               self._time_format.check_time_format,
                               "*")

    def test_compute_next_time(self):
        now = datetime(2016, 1, 20, 15, 11, 0, 0)
        obj = self._time_format(now, "* * * * *")
        time1 = obj.compute_next_time(now)
        time2 = now + timedelta(minutes=1)
        self.assertEqual(time2, time1)

    def test_get_interval(self):
        obj = self._time_format(datetime.now(), "* * * * *")
        self.assertEqual(60, obj.get_min_interval())
