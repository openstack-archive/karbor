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
from karbor.services.operationengine.engine.triggers.timetrigger import\
    time_format_manager
from karbor.tests import base


class TimeFormatManagerTestCase(base.TestCase):

    def setUp(self):
        super(TimeFormatManagerTestCase, self).setUp()

        self._manager = time_format_manager.TimeFormatManager()

    def test_time_format(self):
        self.assertRaisesRegexp(exception.InvalidInput,
                                "Invalid trigger time format type.*abc$",
                                self._manager.check_time_format,
                                'abc', None)

    def test_compute_next_time(self):
        now = datetime(2016, 1, 20, 15, 11, 0, 0)
        time1 = self._manager.compute_next_time("crontab", "* * * * *", now)
        time2 = now + timedelta(minutes=1)
        self.assertEqual(time2, time1)
