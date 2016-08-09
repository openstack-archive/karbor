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
time format base class
"""

import abc
import six


@six.add_metaclass(abc.ABCMeta)
class TimeFormat(object):

    def __init__(self, start_time, pattern):
        """Initiate time format

        :param start_time: The time points after the start_time are valid
        :param pattern: The pattern of the time

        When the start_time and pattern are specified, the time points
        can be calculated and are immutable.
        """
        pass

    @classmethod
    @abc.abstractmethod
    def check_time_format(cls, pattern):
        """Check time format

        :param pattern: The pattern of the time
        """
        pass

    @abc.abstractmethod
    def compute_next_time(self, current_time):
        """Compute next time

        :param current_time: the time before the next time
        """
        pass

    @abc.abstractmethod
    def get_min_interval(self):
        """Get minimum interval of two adjacent time points"""
        pass
