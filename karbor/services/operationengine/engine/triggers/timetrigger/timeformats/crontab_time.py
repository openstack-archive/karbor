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
from karbor.services.operationengine.engine.triggers.timetrigger import\
    timeformats


class Crontab(timeformats.TimeFormat):
    """Crontab."""

    FORMAT_TYPE = "crontab"

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

    @classmethod
    def compute_next_time(cls, pattern, start_time):
        return croniter(pattern, start_time).get_next(datetime)

    @classmethod
    def get_interval(cls, pattern):
        t1 = cls.compute_next_time(pattern, datetime.now())
        t2 = cls.compute_next_time(pattern, t1)
        return timeutils.delta_seconds(t1, t2)
