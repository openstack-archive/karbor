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
Operation classes
"""

from abc import ABCMeta
import six

from karbor import loadables


@six.add_metaclass(ABCMeta)
class TimeFormat(object):

    FORMAT_TYPE = ""

    @classmethod
    def check_time_format(cls, pattern):
        """Check time format

        Only supports absolute time format, like crontab.
        :param pattern: The pattern of the time
        """
        pass

    @classmethod
    def compute_next_time(cls, pattern, start_time):
        """Compute next time

        :param pattern: The pattern of time
        :param start_time: the start time for computing
        """
        pass

    @classmethod
    def get_interval(cls, pattern):
        """Get interval of two adjacent time points

        :param pattern: The pattern of the time
        """
        pass


class TimeFormatHandler(loadables.BaseLoader):

    def __init__(self):
        super(TimeFormatHandler, self).__init__(TimeFormat)


def all_time_formats():
    """Get all trigger time format classes."""
    return TimeFormatHandler().get_all_classes()
