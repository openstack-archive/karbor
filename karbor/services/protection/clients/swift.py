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

from keystoneauth1 import identity
from keystoneauth1 import session as keystone_session
from oslo_config import cfg
from swiftclient import client as swift

SERVICE = 'swift'
swift_client_opts = [
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the swift endpoint. Only used if '
                    'swift_auth_url is unset'),
    cfg.StrOpt(SERVICE + '_catalog_info',
               default='object-store:swift:publicURL',
               help='Info to match when looking for swift in the service '
                    'catalog. Format is: separated values of the form: '
                    '<service_type>:<service_name>:<endpoint_type> - '
                    'Only used if swift_endpoint and swift_auth_url '
                    'are unset'),
    cfg.StrOpt('swift_auth_url',
               help='The URL of the Keystone endpoint'),
    cfg.StrOpt('swift_tenant_name',
               help='Swift tenant/account name. '
                    'Required when connecting to an auth 2.0 system'),
    cfg.StrOpt('swift_user',
               help='Swift user name, if swift_auth_url is set.'),
    cfg.StrOpt('swift_key',
               secret=True,
               help='Swift key for authentication, if swift_auth_url '
                    ' is set.'),
    cfg.IntOpt('swift_retry_attempts',
               default=3,
               help='The number of retries to make for '
                    'Swift operations'),
    cfg.IntOpt('swift_retry_backoff',
               default=2,
               help='The backoff time in seconds '
                    'between Swift retries'),
    cfg.StrOpt('swift_ca_cert_file',
               help='Location of the CA certificate file '
                    'to use for swift client requests.'),
    cfg.BoolOpt('swift_auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Swift.'),
]


def register_opts(conf):
    conf.register_opts(swift_client_opts, group=SERVICE + '_client')


def create(context, conf, **kwargs):
    register_opts(conf)

    client_config = conf.swift_client
    session = kwargs.get('session', None)

    if not session:
        auth = identity.Password(
            auth_url=client_config.swift_auth_url,
            username=client_config.swift_user,
            password=client_config.swift_key,
            project_name=client_config.swift_tenant_name,
        )
        session = keystone_session.Session(auth=auth)

    return swift.Connection(
        session=session,
        insecure=client_config.swift_auth_insecure,
        cacert=client_config.swift_ca_cert_file,
        retries=client_config.swift_retry_attempts,
        starting_backoff=client_config.swift_retry_backoff,
    )
