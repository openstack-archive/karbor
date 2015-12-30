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

"""Utilities and helper functions."""
import os

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
import six

from smaug import exception
from smaug.i18n import _

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def find_config(config_path):
    """Find a configuration file using the given hint.

    :param config_path: Full or relative path to the config.
    :returns: Full path of the config, if it exists.
    :raises: `smaug.exception.ConfigNotFound`

    """
    possible_locations = [
        config_path,
        os.path.join("/var/lib/smaug", "etc", "smaug", config_path),
        os.path.join("/var/lib/smaug", "etc", config_path),
        os.path.join("/var/lib/smaug", config_path),
        "/etc/smaug/%s" % config_path,
    ]

    for path in possible_locations:
        if os.path.exists(path):
            return os.path.abspath(path)

    raise exception.ConfigNotFound(path=os.path.abspath(config_path))


def check_string_length(value, name, min_length=0, max_length=None):
    """Check the length of specified string.

    :param value: the value of the string
    :param name: the name of the string
    :param min_length: the min_length of the string
    :param max_length: the max_length of the string
    """
    if not isinstance(value, six.string_types):
        msg = _("%s is not a string or unicode") % name
        raise exception.InvalidInput(message=msg)

    if len(value) < min_length:
        msg = _("%(name)s has a minimum character requirement of "
                "%(min_length)s.") % {'name': name, 'min_length': min_length}
        raise exception.InvalidInput(message=msg)

    if max_length and len(value) > max_length:
        msg = _("%(name)s has more than %(max_length)s "
                "characters.") % {'name': name, 'max_length': max_length}
        raise exception.InvalidInput(message=msg)


def service_is_up(service):
    """Check whether a service is up based on last heartbeat."""
    last_heartbeat = service['updated_at'] or service['created_at']

    elapsed = (timeutils.utcnow(with_timezone=True) -
               last_heartbeat).total_seconds()
    return abs(elapsed) <= CONF.service_down_time
