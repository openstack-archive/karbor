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
import os

from datetime import timedelta
from dateutil import rrule
from icalendar import Calendar
from oslo_serialization import jsonutils
from oslo_utils import timeutils

from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine.triggers.timetrigger import \
    timeformats


RATE = 2
FREQ_TO_KWARGS = [{'days': RATE*366},
                  {'days': RATE*31},
                  {'days': RATE*7},
                  {'days': RATE},
                  {'hours': RATE},
                  {'minutes': RATE},
                  {'seconds': RATE}]

RREQ_MAP = {"YEARLY": 0,
            "MONTHLY": 1,
            "WEEKLY": 2,
            "DAILY": 3,
            "HOURLY": 4,
            "MINUTELY": 5,
            "SECONDLY": 6}


class ICal(timeformats.TimeFormat):
    """icalendar."""

    def __init__(self, start_time, pattern):
        super(ICal, self).__init__(start_time, pattern)
        cal = Calendar.from_ical(self._decode_calendar_pattern(pattern))
        vevent = cal.walk('VEVENT')[0]
        self.dtstart = start_time
        self.min_freq = self._get_min_freq(vevent)
        self.rrule_obj = self._get_rrule_obj(vevent, start_time)

    @staticmethod
    def _decode_calendar_pattern(pattern):
        try:
            pattern.index('\\')
            pattern_dict = jsonutils.loads('{"pattern": "%s"}' % pattern)
            return pattern_dict["pattern"]
        except Exception:
            return pattern

    @staticmethod
    def _get_rrule_obj(vevent, dtstart):
        rrules = vevent.get('RRULE')
        rrule_list = rrules if isinstance(rrules, list) else [rrules]
        rrule_str = os.linesep.join(recur.to_ical().decode("utf-8")
                                    for recur in rrule_list)
        return rrule.rrulestr(rrule_str, dtstart=dtstart, cache=False)

    @staticmethod
    def _get_min_freq(vevent):
        recur = vevent.decoded("RRULE")
        recur_list = recur if isinstance(recur, list) else [recur]
        freq_list = []
        for recur in recur_list:
            for freq in recur.get("FREQ"):
                freq_list.append(RREQ_MAP[freq.upper()])
        return max(freq_list)

    @classmethod
    def check_time_format(cls, pattern):
        """Check time format

        :param pattern: The pattern of the icalendar time
        """
        try:
            cal_obj = Calendar.from_ical(cls._decode_calendar_pattern(pattern))
        except Exception:
            msg = (_("The trigger pattern(%s) is invalid") % pattern)
            raise exception.InvalidInput(msg)

        try:
            vevent = cal_obj.walk('VEVENT')[0]
        except Exception:
            msg = (_("The trigger pattern(%s) must include less than one "
                     "VEVENT component") % pattern)
            raise exception.InvalidInput(msg)

        try:
            vevent.decoded('RRULE')
        except Exception:
            msg = (_("The first VEVENT component of trigger pattern(%s) must "
                     "include less than one RRULE property") % pattern)
            raise exception.InvalidInput(msg)

    def compute_next_time(self, current_time):
        """Compute next time

        :param current_time: the time before the next time
        :return datetime or None
        """
        next_time = self.rrule_obj.after(current_time)
        return next_time if next_time else None

    def get_min_interval(self):
        """Get minimum interval of two adjacent time points

        :return int(seconds) or None
        """
        gen = self.rrule_obj
        kwargs = FREQ_TO_KWARGS[self.min_freq]
        endtime = self.dtstart + timedelta(**kwargs)

        deltas = []
        t0 = None
        for dt in gen:
            if dt > endtime:
                break
            t1 = t0
            t0 = dt
            if t1 is None or t0 is None or dt <= self.dtstart:
                continue
            delta = timeutils.delta_seconds(t1, t0)
            if delta:
                deltas.append(delta)
        if len(deltas):
            return min(deltas)
        else:
            return None
