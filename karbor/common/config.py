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
    cfg.StrOpt('state_path',
               default='/var/lib/karbor',
               deprecated_name='pybasedir',
               help="Top-level directory for maintaining karbor's state"),
]

debug_opts = [
]

CONF.register_cli_opts(core_opts)
CONF.register_cli_opts(debug_opts)

global_opts = [
    cfg.IntOpt('service_down_time',
               default=60,
               help='Maximum time since last check-in for a service to be '
                    'considered up'),
    cfg.StrOpt('operationengine_topic',
               default='karbor-operationengine',
               help='The topic that OperationEngine nodes listen on'),
    cfg.StrOpt('operationengine_manager',
               default='karbor.services.operationengine.manager.'
               'OperationEngineManager',
               help='Full class name for the Manager for OperationEngine'),
    cfg.StrOpt('protection_topic',
               default='karbor-protection',
               help='The topic that protection nodes listen on'),
    cfg.StrOpt('protection_manager',
               default='karbor.services.protection.manager.ProtectionManager',
               help='Full class name for the Manager for Protection'),
    cfg.HostAddressOpt('host',
                       default=socket.gethostname(),
                       help='Name of this node.  This can be an opaque '
                            'identifier. It is not necessarily a host '
                            'name, FQDN, or IP address.'),
    cfg.StrOpt('auth_strategy',
               default='keystone',
               choices=['noauth', 'keystone'],
               help='The strategy to use for auth. Supports noauth or '
                    'keystone.'),
]

CONF.register_opts(global_opts)


service_client_opts = [
    cfg.StrOpt('service_name',
               help='The name of service registered in Keystone'),

    cfg.StrOpt('service_type',
               help='The type of service registered in Keystone'),

    cfg.StrOpt('version',
               help='The version of service client'),

    cfg.StrOpt('region_id',
               default='RegionOne',
               help='The region id which the service belongs to.'),

    cfg.StrOpt('interface',
               default='internal',
               help='The network interface of the endpoint. Valid '
                    'values are: public, admin, internal.'),

    cfg.StrOpt('ca_cert_file',
               help='Location of the CA certificate file '
                    'to use for client requests in SSL connections.'),

    cfg.BoolOpt('auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to service.')
]


keystone_client_opts = [
    cfg.StrOpt('auth_uri',
               default='',
               help='Unversioned keystone url in format like '
                    'http://0.0.0.0:5000.')]


def list_opts():
    yield 'clients_keystone', keystone_client_opts


for group, opts in list_opts():
    CONF.register_opts(opts, group=group)
