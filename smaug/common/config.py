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

"""Command-line flag library.

Emulates gflags by wrapping cfg.ConfigOpts.

The idea is to move fully to cfg eventually, and this wrapper is a
stepping stone.

"""

import socket

from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF
logging.register_options(CONF)

core_opts = [
    cfg.StrOpt('api_paste_config',
               default="api-paste.ini",
               help='File name for the paste.deploy config for smaug-api')
]

debug_opts = [
]

CONF.register_cli_opts(core_opts)
CONF.register_cli_opts(debug_opts)

global_opts = [
    cfg.StrOpt('scheduler_topic',
               default='Smaug-scheduler',
               help='The topic that scheduler nodes listen on'),
    cfg.StrOpt('scheduler_manager',
               default='Smaug.scheduler.manager.SchedulerManager',
               help='Full class name for the Manager for scheduler'),
    cfg.StrOpt('host',
               default=socket.gethostname(),
               help='Name of this node.  This can be an opaque identifier. '
                    'It is not necessarily a host name, FQDN, or IP address.'),
    cfg.StrOpt('auth_strategy',
               default='keystone',
               choices=['noauth', 'keystone'],
               help='The strategy to use for auth. Supports noauth or '
                    'keystone.'),
]

CONF.register_opts(global_opts)
