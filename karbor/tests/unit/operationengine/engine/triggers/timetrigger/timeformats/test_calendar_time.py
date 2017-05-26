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

import re

from datetime import datetime
from oslo_serialization import jsonutils

from karbor import exception
from karbor.services.operationengine.engine.triggers.timetrigger.timeformats \
    import calendar_time
from karbor.tests import base


class CalendarTimeTestCase(base.TestCase):

    def test_invalid_pattern(self):
        patterns = [
            "     ",

            "DTSTART:20070220T170000Z\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYHOUR=17;BYMINUTE=1\n",

            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "DTSTART:20070220T170000\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYHOUR=17;BYMINUTE=6\n"
            "END:VCALENDAR",

            "BEGIN:VCALENDAR\n"
            "DTSTART:20070220T170000\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYHOUR=17;BYMINUTE=6\n"
            "END:VEVENT\n"
            "END:VCALENDAR",
        ]

        regexp = re.compile("^The trigger pattern.* is invalid$", re.DOTALL)
        for pattern in patterns:
            self.assertRaisesRegex(exception.InvalidInput,
                                   regexp,
                                   calendar_time.ICal.check_time_format,
                                   pattern)

        patterns = [
            "BEGIN:VCALENDAR\n"
            "END:VCALENDAR",

            "BEGIN:VCALENDAR\n"
            "DTSTART:20070220T170000\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYHOUR=17;BYMINUTE=6\n"
            "END:VCALENDAR",

            "BEGIN:VCALENDAR\n"
            "BEGIN:VTODO\n"
            "END:VTODO\n"
            "END:VCALENDAR",
        ]

        regexp = re.compile("^The trigger pattern.* must include less than "
                            "one VEVENT component$", re.DOTALL)
        for pattern in patterns:
            self.assertRaisesRegex(exception.InvalidInput,
                                   regexp,
                                   calendar_time.ICal.check_time_format,
                                   pattern)

        patterns = [
            "BEGIN:VEVENT\n"
            "END:VEVENT",

            "BEGIN:VCALENDAR\n"
            "BEGIN:VEVENT\n"
            "END:VEVENT\n"
            "END:VCALENDAR",

            "BEGIN:VEVENT\n"
            "DTSTART:20070220T170000Z\n"
            "END:VEVENT",
        ]

        regexp = re.compile("^The first VEVENT component of trigger pattern.* "
                            "must include less than one RRULE property$",
                            re.DOTALL)
        for pattern in patterns:
            self.assertRaisesRegex(exception.InvalidInput,
                                   regexp,
                                   calendar_time.ICal.check_time_format,
                                   pattern)

    def test_valid_pattern(self):
        pattern = "BEGIN:VEVENT\nRRULE:FREQ=MINUTELY;INTERVAL=60;\nEND:VEVENT"
        self.assertIsNone(calendar_time.ICal.check_time_format(pattern))

    def test_escape_valid_pattern(self):
        pattern0 = "BEGIN:VEVENT\\nRRULE:FREQ=HOURLY;INTERVAL=1;\\nEND:VEVENT"
        self.assertIsNone(calendar_time.ICal.check_time_format(pattern0))

        pattern1 = "BEGIN:VEVENT\nRRULE:FREQ=HOURLY;INTERVAL=1;\nEND:VEVENT"
        properties = {"format": "calendar",
                      "pattern": pattern1}
        body = {"trigger_info": {"name": "test",
                                 "type": "time",
                                 "properties": properties,
                                 }}
        quest = jsonutils.dumps(body)
        recieve = jsonutils.loads(quest)
        trigger_info = recieve["trigger_info"]
        trigger_property = trigger_info.get("properties", None)
        pattern_ = trigger_property.get("pattern", None)

        self.assertIsNone(calendar_time.ICal.check_time_format(pattern_))

    def test_compute_next_time(self):
        pattern = (
            "BEGIN:VEVENT\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYHOUR=17;BYMINUTE=1\n"
            "END:VEVENT"
        )
        dtstart = datetime(2016, 2, 20, 17, 0, 0)
        time_obj = calendar_time.ICal(dtstart, pattern)
        now = datetime(2016, 2, 20, 15, 11, 0)
        time1 = time_obj.compute_next_time(now)
        time2 = datetime(2016, 2, 20, 17, 1, 0)
        self.assertEqual(time2, time1)
        now = datetime(2016, 3, 20, 15, 11, 0)
        time1 = time_obj.compute_next_time(now)
        time2 = datetime(2016, 3, 26, 17, 1, 0)
        self.assertEqual(time2, time1)

        pattern = (
            "BEGIN:VEVENT\n"
            "RRULE:FREQ=WEEKLY;BYDAY=MO,WE,FR;BYHOUR=10;BYMINUTE=0\n"
            "RRULE:FREQ=WEEKLY;BYDAY=TU,TH,SA;BYHOUR=20;BYMINUTE=0\n"
            "END:VEVENT"
        )
        dtstart = datetime(2016, 2, 20, 17, 0, 0)
        time_obj = calendar_time.ICal(dtstart, pattern)
        now = datetime(2016, 7, 31, 15, 11, 0)
        time1 = time_obj.compute_next_time(now)
        time2 = datetime(2016, 8, 1, 10, 0, 0)
        self.assertEqual(time2, time1)
        time1 = time_obj.compute_next_time(time2)
        time2 = datetime(2016, 8, 2, 20, 0, 0)
        self.assertEqual(time2, time1)
        time1 = time_obj.compute_next_time(time2)
        time2 = datetime(2016, 8, 3, 10, 0, 0)
        self.assertEqual(time2, time1)

    def test_get_min_interval(self):
        pattern = (
            "BEGIN:VEVENT\n"
            "RRULE:FREQ=WEEKLY;INTERVAL=1;BYHOUR=17;BYMINUTE=1\n"
            "END:VEVENT"
        )
        dtstart = datetime(2016, 2, 20, 17, 0, 0)
        time_obj = calendar_time.ICal(dtstart, pattern)
        self.assertEqual(604800, time_obj.get_min_interval())

        pattern = (
            "BEGIN:VEVENT\n"
            "RRULE:FREQ=WEEKLY;COUNT=1\n"
            "END:VEVENT"
        )
        dtstart = datetime(2016, 2, 20, 17, 0, 0)
        time_obj = calendar_time.ICal(dtstart, pattern)
        self.assertIsNone(time_obj.get_min_interval())
