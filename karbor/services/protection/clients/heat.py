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
from keystoneclient.v2_0 import client as kc

from oslo_log import log as logging
from karbor.i18n import _LE, _LI

LOG = logging.getLogger(__name__)

SERVICE = 'heat'

KEYSTONECLIENT_VERSION = (3, 0)
HEATCLIENT_VERSION = '1'


def create(context, conf, **kwargs):
    auth_url = kwargs["auth_url"]
    username = kwargs["username"]
    password = kwargs["password"]
    tenant_name = context.project_name
    LOG.info(_LI('Creating heat client with url %s.'), auth_url)
    try:
        keystone = kc.Client(version=KEYSTONECLIENT_VERSION,
                             username=username,
                             tenant_name=tenant_name,
                             password=password,
                             auth_url=auth_url)

        auth_token = keystone.auth_ref['token']['id']
        heat_endpoint = ''
        services = keystone.auth_ref['serviceCatalog']
        for service in services:
            if service['name'] == 'heat':
                heat_endpoint = service['endpoints'][0]['publicURL']
        heat = hc.Client(HEATCLIENT_VERSION, endpoint=heat_endpoint,
                         token=auth_token)
        return heat
    except Exception:
        LOG.error(_LE('Creating heat client with url %s.'), auth_url)
        raise
