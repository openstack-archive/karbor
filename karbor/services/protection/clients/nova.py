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

from novaclient import client as nc
from oslo_config import cfg
from oslo_log import log as logging
from karbor.i18n import _LI, _LE
from karbor.services.protection import utils

LOG = logging.getLogger(__name__)

SERVICE = "nova"
nova_client_opts = [
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the nova endpoint. '
                    '<endpoint_url>'),
    cfg.StrOpt(SERVICE + '_catalog_info',
               default='compute:nova:publicURL',
               help='Info to match when looking for nova in the service '
               'catalog. Format is: separated values of the form: '
               '<service_type>:<service_name>:<endpoint_type> - '
               'Only used if nova_endpoint is unset'),
    cfg.StrOpt(SERVICE + '_ca_cert_file',
               default=None,
               help='Location of the CA certificate file '
                    'to use for client requests in SSL connections.'),
    cfg.BoolOpt(SERVICE + '_auth_insecure',
                default=True,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Nova.'),
]

cfg.CONF.register_opts(nova_client_opts, group=SERVICE + '_client')

NOVACLIENT_VERSION = '2'


def create(context, conf):
    conf.register_opts(nova_client_opts, group=SERVICE + '_client')
    try:
        url = utils.get_url(SERVICE, context, conf,
                            append_project_fmt='%(url)s/%(project)s')
    except Exception:
        LOG.error(_LE("Get nova service endpoint url failed."))
        raise

    LOG.info(_LI('Creating nova client with url %s.'), url)

    extensions = nc.discover_extensions(NOVACLIENT_VERSION)

    args = {
        'project_id': context.project_id,
        'auth_token': context.auth_token,
        'extensions': extensions,
        'cacert': conf.nova_client.nova_ca_cert_file,
        'insecure': conf.nova_client.nova_auth_insecure,
    }

    client = nc.Client(NOVACLIENT_VERSION, **args)
    client.client.set_management_url(url)

    return client
