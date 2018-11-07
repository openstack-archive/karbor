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

from freezerclient.v1 import client as freezer_client
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import config
from karbor.services.protection.clients import utils

LOG = logging.getLogger(__name__)

SERVICE = "freezer"
freezer_client_opts = [
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the freezer endpoint.'),
    cfg.StrOpt(SERVICE + '_catalog_info',
               default='backup:freezer:publicURL',
               help='Info to match when looking for freezer in the service '
                    'catalog. Format is: separated values of the form: '
                    '<service_type>:<service_name>:<endpoint_type> - '
                    'Only used if freezer_endpoint is unset'),
    cfg.StrOpt(SERVICE + '_ca_cert_file',
               help='Location of the CA certificate file '
                    'to use for client requests in SSL connections.'),
    cfg.BoolOpt(SERVICE + '_auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Freezer.'),
]

CONFIG_GROUP = '%s_client' % SERVICE
CONF = cfg.CONF
CONF.register_opts(config.service_client_opts, group=CONFIG_GROUP)
CONF.register_opts(config.keystone_client_opts, group=CONFIG_GROUP)
CONF.register_opts(freezer_client_opts, group=CONFIG_GROUP)
CONF.set_default('service_name', 'freezer', CONFIG_GROUP)
CONF.set_default('service_type', 'backup', CONFIG_GROUP)


def create(context, conf, **kwargs):
    conf.register_opts(freezer_client_opts, group=CONFIG_GROUP)

    client_config = conf[CONFIG_GROUP]
    url = utils.get_url(SERVICE, context, client_config,
                        append_project_fmt='%(url)s/%(project)s', **kwargs)

    if kwargs.get('session'):
        return freezer_client.Client(session=kwargs.get('session'),
                                     endpoint=url)
    args = {
        'project_id': context.project_id,
        'project_name': context.project_name,
        'cacert': client_config.freezer_ca_cert_file,
        'insecure': client_config.freezer_auth_insecure,
        'endpoint': url,
        'token': context.auth_token,
        'auth_url': client_config.auth_uri
    }
    return freezer_client.Client(**args)
