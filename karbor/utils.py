# Licensed under the Apache License, Version 2.0 (the "License"); you may
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
import ast
import os

from keystoneclient import discover as ks_discover
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils
from oslo_utils import strutils
from oslo_utils import timeutils

from karbor import exception
from karbor.i18n import _, _LE
from stevedore import driver

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def find_config(config_path):
    """Find a configuration file using the given hint.

    :param config_path: Full or relative path to the config.
    :returns: Full path of the config, if it exists.
    :raises: `karbor.exception.ConfigNotFound`

    """
    possible_locations = [
        config_path,
        os.path.join("/var/lib/karbor", "etc", "karbor", config_path),
        os.path.join("/var/lib/karbor", "etc", config_path),
        os.path.join("/var/lib/karbor", config_path),
        "/etc/karbor/%s" % config_path,
    ]

    for path in possible_locations:
        if os.path.exists(path):
            return os.path.abspath(path)

    raise exception.ConfigNotFound(path=os.path.abspath(config_path))


def service_is_up(service):
    """Check whether a service is up based on last heartbeat."""
    last_heartbeat = service['updated_at'] or service['created_at']

    elapsed = (timeutils.utcnow(with_timezone=True) -
               last_heartbeat).total_seconds()
    return abs(elapsed) <= CONF.service_down_time


def remove_invalid_filter_options(context, filters,
                                  allowed_search_options):
    """Remove search options that are not valid for non-admin API/context."""

    if context.is_admin:
        # Allow all options
        return
    # Otherwise, strip out all unknown options
    unknown_options = [opt for opt in filters
                       if opt not in allowed_search_options]
    bad_options = ", ".join(unknown_options)
    LOG.debug("Removing options '%s' from query.", bad_options)
    for opt in unknown_options:
        del filters[opt]


def check_filters(filters):
    for k, v in filters.items():
        try:
            filters[k] = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            LOG.debug('Could not evaluate value %s, assuming string', v)


def is_valid_boolstr(val):
    """Check if the provided string is a valid bool string or not."""
    val = str(val).lower()
    return val in ('true', 'false', 'yes', 'no', 'y', 'n', '1', '0')


def get_bool_param(param_string, params):
    param = params.get(param_string, False)
    if not is_valid_boolstr(param):
        msg = _('Value %(param)s for %(param_string)s is not a '
                'boolean.') % {'param': param, 'param_string': param_string}
        raise exception.InvalidParameterValue(err=msg)

    return strutils.bool_from_string(param, strict=True)


def load_class(namespace, plugin_name):
    try:
        LOG.debug('Start load plugin %s. ', plugin_name)
        # Try to resolve plugin by name
        mgr = driver.DriverManager(namespace, plugin_name)
        return mgr.driver
    except RuntimeError as e1:
        # fallback to class name
        try:
            return importutils.import_class(plugin_name)
        except ImportError as e2:
            LOG.error(_LE("Error loading plugin by name, %s"), e1)
            LOG.error(_LE("Error loading plugin by class, %s"), e2)
            raise ImportError(_("Class not found."))


def load_plugin(namespace, plugin_name, *args, **kwargs):
    plugin_class = load_class(namespace, plugin_name)
    return plugin_class(*args, **kwargs)


def get_auth_uri(v3=True):
    # Look for the keystone auth_uri in the configuration. First we
    # check the [clients_keystone] section, and if it is not set we
    # look in [keystone_authtoken]
    if cfg.CONF.clients_keystone.auth_uri:
        discover = ks_discover.Discover(
            auth_url=cfg.CONF.clients_keystone.auth_uri)
        return discover.url_for('3.0')
    else:
        # Import auth_token to have keystone_authtoken settings setup.
        importutils.import_module('keystonemiddleware.auth_token')
        auth_uri = cfg.CONF.keystone_authtoken.auth_uri
        return auth_uri.replace('v2.0', 'v3') if auth_uri and v3 else auth_uri
