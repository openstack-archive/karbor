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

import os

from abclient import client
from oslo_config import cfg
from oslo_log import log as logging

from karbor import utils

EISOO_JOB_TYPE = (ORACLE_JOB_TYPE) = (1)
EISOO_JOB_STATUS = (RUNNING, SUCCESS, FAILED) = (4, 32, 64)

SERVICE = "eisoo"
eisoo_client_opts = [
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the eisoo endpoint.'),
    cfg.StrOpt(SERVICE + '_app_id',
               help='App id for eisoo authentication.'),
    cfg.StrOpt(SERVICE + '_app_secret',
               secret=True,
               help='App secret for eisoo authentication.'),
]

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


def create(context, conf):
    config_dir = utils.find_config(CONF.provider_config_dir)
    config_file = os.path.abspath(os.path.join(config_dir,
                                               'eisoo.conf'))
    config = cfg.ConfigOpts()
    config(args=['--config-file=' + config_file])
    config.register_opts(eisoo_client_opts,
                         group=SERVICE + '_client')

    LOG.info('Creating eisoo client with url %s.',
             config.eisoo_client.eisoo_endpoint)
    abclient = client.ABClient(config.eisoo_client.eisoo_endpoint,
                               config.eisoo_client.eisoo_app_id,
                               config.eisoo_client.eisoo_app_secret)

    return abclient
