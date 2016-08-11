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

"""
Manage all time formats.
"""

from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine.triggers.timetrigger import\
    timeformats


class TimeFormatManager(object):
    """Manage all time format classes"""

    def __init__(self):
        super(TimeFormatManager, self).__init__()

        all_cls = timeformats.all_time_formats()
        self._timeformat_cls_map = {cls.FORMAT_TYPE:
                                    cls for cls in all_cls}

    def _get_timeformat_cls(self, format_type):
        if format_type not in self._timeformat_cls_map:
            msg = (_("Invalid trigger time format type:%s") % format_type)
            raise exception.InvalidInput(msg)

        return self._timeformat_cls_map[format_type]

    def check_time_format(self, format_type, pattern):
        """Check time format

        :param format_type: the type of time format, like crontab
        :param pattern: The pattern of the time
        """
        cls = self._get_timeformat_cls(format_type)
        cls.check_time_format(pattern)

    def compute_next_time(self, format_type, pattern, start_time):
        """Compute next time

        :param format_type: the type of time format, like crontab
        :param pattern: The pattern of the time
        :param start_time: the start time for computing
        """
        cls = self._get_timeformat_cls(format_type)
        return cls.compute_next_time(pattern, start_time)

    def get_interval(self, format_type, pattern):
        """Get interval of two adjacent time points

        :param format_type: the type of time format, like crontab
        :param pattern: The pattern of the time
        """
        cls = self._get_timeformat_cls(format_type)
        return cls.get_interval(pattern)
