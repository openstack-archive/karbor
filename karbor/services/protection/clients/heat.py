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

from heatclient import client as hc
from keystoneclient.v3 import client as kc_v3
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import config
from karbor.services.protection.clients import utils

LOG = logging.getLogger(__name__)

SERVICE = 'heat'
heat_client_opts = [
    cfg.StrOpt('region_id',
               default='RegionOne',
               help='The region id which the service belongs to.'),
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the heat endpoint.'),
    cfg.StrOpt(SERVICE + '_catalog_info',
               default='orchestration:heat:publicURL',
               help='Info to match when looking for heat in the service '
               'catalog. Format is: separated values of the form: '
               '<service_type>:<service_name>:<endpoint_type> - '
               'Only used if cinder_endpoint is unset'),
    cfg.StrOpt(SERVICE + '_ca_cert_file',
               help='Location of the CA certificate file '
                    'to use for client requests in SSL connections.'),
    cfg.BoolOpt(SERVICE + '_auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Cinder.'),
]

CONFIG_GROUP = '%s_client' % SERVICE
CONF = cfg.CONF
CONF.register_opts(config.service_client_opts, group=CONFIG_GROUP)
CONF.register_opts(heat_client_opts, group=CONFIG_GROUP)
CONF.set_default('service_name', 'heat', CONFIG_GROUP)
CONF.set_default('service_type', 'orchestration', CONFIG_GROUP)

KEYSTONECLIENT_VERSION = (3, 0)
HEATCLIENT_VERSION = '1'


def create(context, conf, **kwargs):
    cfg.CONF.register_opts(heat_client_opts, group=CONFIG_GROUP)

    client_config = conf[CONFIG_GROUP]
    if kwargs.get("auth_url", None):
        return _create_client_with_auth_url(context, client_config, **kwargs)
    else:
        return _create_client_with_tenant(context, client_config, **kwargs)


def _create_client_with_auth_url(context, client_config, **kwargs):
    auth_url = kwargs["auth_url"]
    username = kwargs["username"]
    password = kwargs["password"]
    tenant_name = context.project_name
    cacert = client_config.heat_ca_cert_file
    insecure = client_config.heat_auth_insecure
    LOG.debug('Creating heat client with auth url %s.', auth_url)
    try:
        keystone = kc_v3.Client(version=KEYSTONECLIENT_VERSION,
                                username=username,
                                tenant_name=tenant_name,
                                password=password,
                                auth_url=auth_url)

        auth_token = keystone.auth_token
        heat_endpoint = ''
        services = keystone.service_catalog.catalog['catalog']
        for service in services:
            if service['name'] == 'heat':
                endpoints = service['endpoints']
                for endpoint in endpoints:
                    if endpoint['interface'] == 'public':
                        heat_endpoint = endpoint['url']
        heat = hc.Client(HEATCLIENT_VERSION, endpoint=heat_endpoint,
                         token=auth_token, cacert=cacert, insecure=insecure)
        return heat
    except Exception:
        LOG.error('Creating heat client with url %s.', auth_url)
        raise


def _create_client_with_tenant(context, client_config, **kwargs):
    url = utils.get_url(SERVICE, context, client_config,
                        append_project_fmt='%(url)s/%(project)s', **kwargs)
    LOG.debug('Creating heat client with url %s.', url)

    if kwargs.get('session'):
        return hc.Client(HEATCLIENT_VERSION, session=kwargs.get('session'),
                         endpoint=url)

    args = {
        'endpoint': url,
        'token': context.auth_token,
        'cacert': client_config.heat_ca_cert_file,
        'insecure': client_config.heat_auth_insecure,
    }
    return hc.Client(HEATCLIENT_VERSION, **args)
