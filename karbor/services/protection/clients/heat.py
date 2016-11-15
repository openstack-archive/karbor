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
from karbor.i18n import _LE, _LI
from karbor.services.protection import utils

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
               default=None,
               help='Location of the CA certificate file '
                    'to use for client requests in SSL connections.'),
    cfg.BoolOpt(SERVICE + '_auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Cinder.'),
]

cfg.CONF.register_opts(heat_client_opts, group=SERVICE + '_client')

KEYSTONECLIENT_VERSION = (3, 0)
HEATCLIENT_VERSION = '1'


def create(context, conf, **kwargs):
    cfg.CONF.register_opts(heat_client_opts, group=SERVICE + '_client')
    auth_url = kwargs.get("auth_url", None)
    if auth_url is not None:
        return create_heat_client_with_auth_url(context, conf, **kwargs)
    else:
        return create_heat_client_with_tenant(context, conf)


def create_heat_client_with_auth_url(context, conf, **kwargs):
    auth_url = kwargs["auth_url"]
    username = kwargs["username"]
    password = kwargs["password"]
    tenant_name = context.project_name
    cacert = conf.heat_client.heat_ca_cert_file
    insecure = conf.heat_client.heat_auth_insecure
    LOG.info(_LI('Creating heat client with auth url %s.'), auth_url)
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
        LOG.error(_LE('Creating heat client with url %s.'), auth_url)
        raise


def create_heat_client_with_tenant(context, conf):
    cacert = conf.heat_client.heat_ca_cert_file
    insecure = conf.heat_client.heat_auth_insecure

    conf.register_opts(heat_client_opts, group=SERVICE + '_client')
    try:
        url = utils.get_url(SERVICE, context, conf,
                            append_project_fmt='%(url)s/%(project)s')
    except Exception:
        LOG.error(_LE("Get heat service endpoint url failed."))
        raise

    try:
        LOG.info(_LI('Creating heat client with url %s.'), url)
        heat = hc.Client(HEATCLIENT_VERSION, endpoint=url,
                         token=context.auth_token, cacert=cacert,
                         insecure=insecure)
        return heat
    except Exception:
        LOG.error(_LE('Creating heat client with endpoint fails.'))
        raise
