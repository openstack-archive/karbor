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

from glanceclient import client as gc
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import config
from karbor.services.protection.clients import utils

LOG = logging.getLogger(__name__)

SERVICE = 'glance'
glance_client_opts = [
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the glance endpoint.'),
    cfg.StrOpt(SERVICE + '_catalog_info',
               default='image:glance:publicURL',
               help='Info to match when looking for glance in the service '
               'catalog. Format is: separated values of the form: '
               '<service_type>:<service_name>:<endpoint_type> - '
               'Only used if glance_endpoint is unset'),
    cfg.StrOpt(SERVICE + '_ca_cert_file',
               help='Location of the CA certificate file '
                    'to use for client requests in SSL connections.'),
    cfg.BoolOpt(SERVICE + '_auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Glance.'),
]

CONFIG_GROUP = '%s_client' % SERVICE
CONF = cfg.CONF
CONF.register_opts(config.service_client_opts, group=CONFIG_GROUP)
CONF.register_opts(glance_client_opts, group=CONFIG_GROUP)
CONF.set_default('service_name', 'glance', CONFIG_GROUP)
CONF.set_default('service_type', 'image', CONFIG_GROUP)

GLANCECLIENT_VERSION = '2'


def create(context, conf, **kwargs):
    conf.register_opts(glance_client_opts, group=CONFIG_GROUP)

    client_config = conf[CONFIG_GROUP]
    url = utils.get_url(SERVICE, context, client_config, **kwargs)
    LOG.debug("Creating glance client with url %s.", url)

    if kwargs.get('session'):
        return gc.Client(GLANCECLIENT_VERSION, session=kwargs.get('session'),
                         endpoint=url)

    args = {
        'endpoint': url,
        'token': context.auth_token,
        'cacert': client_config.glance_ca_cert_file,
        'insecure': client_config.glance_auth_insecure,
    }
    return gc.Client(GLANCECLIENT_VERSION, **args)
