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
from smaug.i18n import _LE, _LI
from smaug.services.protection import utils

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
]

cfg.CONF.register_opts(glance_client_opts, group=SERVICE + '_client')

GLANCECLIENT_VERSION = '2'


def create(context):
    try:
        url = utils.get_url(SERVICE, context)
    except Exception:
        LOG.error(_LE("Get glance service endpoint url failed"))
        raise

    LOG.info(_LI("Creating glance client with url %s."), url)

    args = {
        'endpoint': url,
        'token': context.auth_token,
    }

    return gc.Client(GLANCECLIENT_VERSION, **args)
