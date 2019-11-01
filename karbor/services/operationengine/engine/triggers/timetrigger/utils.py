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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
import six
from stevedore import driver as import_driver

from karbor import exception
from karbor.i18n import _

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def get_time_format_class():
    return import_driver.DriverManager(
        'karbor.operationengine.engine.timetrigger.time_format',
        CONF.time_format).driver


def compute_next_run_time(start_time, end_time, timer):
    next_time = timer.compute_next_time(start_time)
    if next_time and (not end_time or next_time <= end_time):
        return next_time
    return None


def check_and_get_datetime(time, time_name):
    if not time:
        return None

    if isinstance(time, datetime):
        return time

    if not isinstance(time, six.string_types):
        msg = (_("The trigger %(name)s(type = %(vtype)s) is "
                 "not an instance of string") %
               {"name": time_name, "vtype": type(time)})
        raise exception.InvalidInput(msg)

    try:
        time = timeutils.parse_strtime(time, fmt='%Y-%m-%d %H:%M:%S')
    except Exception:
        msg = (_("The format of trigger %s is not correct") % time_name)
        raise exception.InvalidInput(msg)

    return time


def check_trigger_definition(trigger_definition):
    """Check trigger definition

    All the time instances of trigger_definition are in UTC,
    including start_time, end_time
    """
    tf_cls = get_time_format_class()

    pattern = trigger_definition.get("pattern", None)
    tf_cls.check_time_format(pattern)

    start_time = trigger_definition.get("start_time", None)
    if not start_time:
        msg = _("The trigger\'s start time is unknown")
        raise exception.InvalidInput(msg)
    start_time = check_and_get_datetime(start_time, "start_time")

    interval = tf_cls(start_time, pattern).get_min_interval()
    if interval is not None and interval < CONF.min_interval:
        msg = (_("The interval of two adjacent time points "
                 "is less than %d") % CONF.min_interval)
        raise exception.InvalidInput(msg)

    window = trigger_definition.get("window", CONF.min_window_time)
    if not isinstance(window, int):
        try:
            window = int(window)
        except Exception:
            msg = (_("The trigger windows(%s) is not integer") % window)
            raise exception.InvalidInput(msg)

    if window < CONF.min_window_time or window > CONF.max_window_time:
        msg = (_("The trigger windows %(window)d must be between "
                 "%(min_window)d and %(max_window)d") %
               {"window": window,
                "min_window": CONF.min_window_time,
                "max_window": CONF.max_window_time})
        raise exception.InvalidInput(msg)

    end_time = trigger_definition.get("end_time", None)
    end_time = check_and_get_datetime(end_time, "end_time")

    if end_time and end_time <= start_time:
        msg = (_("The trigger's start time(%(start_time)s) is "
                 "bigger than end time(%(end_time)s)") %
               {'start_time': start_time, 'end_time': end_time})
        LOG.error(msg)
        raise exception.InvalidInput(msg)
    valid_trigger_property = trigger_definition.copy()
    valid_trigger_property['window'] = window
    valid_trigger_property['start_time'] = start_time
    valid_trigger_property['end_time'] = end_time
    return valid_trigger_property


def check_configuration():
    min_window = CONF.min_window_time
    max_window = CONF.max_window_time
    min_interval = CONF.min_interval

    if not (min_window < max_window and (max_window * 2 <= min_interval)):
        msg = (_('Configurations of time trigger are invalid'))
        raise exception.InvalidInput(msg)


def get_timer(trigger_property):
    tf_cls = get_time_format_class()
    timer = tf_cls(trigger_property['start_time'],
                   trigger_property['pattern'])
    return timer
