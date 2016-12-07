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

from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import config
from karbor.common import karbor_keystone_plugin
from karborclient import client as karbor_client

LOG = logging.getLogger(__name__)

CONFIG_GROUP = 'karbor_client'
CONF = cfg.CONF
CONF.register_opts(config.service_client_opts,
                   group=CONFIG_GROUP)


def get_karbor_endpoint():
    try:
        sc_cfg = CONF[CONFIG_GROUP]
        kc_plugin = karbor_keystone_plugin.KarborKeystonePlugin()
        url = kc_plugin.get_service_endpoint(
            sc_cfg.service_name, sc_cfg.service_type,
            sc_cfg.region_id, sc_cfg.interface)

        return url.replace("$(", "%(")
    except Exception:
        raise


def create(context, **kwargs):
    endpoint = kwargs.get('endpoint')
    if not endpoint:
        endpoint = get_karbor_endpoint() % {"project_id": context.project_id}

    LOG.debug("Creating karbor client with url %s.", endpoint)

    sc_cfg = CONF[CONFIG_GROUP]
    args = {
        'version': sc_cfg.version,
        'endpoint': endpoint,
        'token': context.auth_token,
        'cacert': sc_cfg.ca_cert_file,
        'insecure': sc_cfg.auth_insecure,
    }

    return karbor_client.Client(**args)
