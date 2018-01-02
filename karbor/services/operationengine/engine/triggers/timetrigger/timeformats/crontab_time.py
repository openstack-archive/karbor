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

from croniter import croniter
from datetime import datetime
from oslo_utils import timeutils

from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine.triggers.timetrigger import \
    timeformats


class Crontab(timeformats.TimeFormat):

    def __init__(self, start_time, pattern):
        self._start_time = start_time
        self._pattern = pattern
        super(Crontab, self).__init__(start_time, pattern)

    @classmethod
    def check_time_format(cls, pattern):
        if not pattern:
            msg = (_("The trigger pattern is None"))
            raise exception.InvalidInput(msg)

        try:
            croniter(pattern)
        except Exception:
            msg = (_("The trigger pattern(%s) is invalid") % pattern)
            raise exception.InvalidInput(msg)

    def compute_next_time(self, current_time):
        time = current_time if current_time >= self._start_time else (
            self._start_time)
        return croniter(self._pattern, time).get_next(datetime)

    def get_min_interval(self):
        try:
            t1 = self.compute_next_time(datetime.now())
            t2 = self.compute_next_time(t1)
            return timeutils.delta_seconds(t1, t2)
        except Exception:
            return None
