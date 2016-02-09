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

"""
OperationEngine Service
"""

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

from smaug import manager
from smaug.services.protection import api as protection_api

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class OperationEngineManager(manager.Manager):
    """Smaug OperationEngine Manager."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, service_name=None,
                 *args, **kwargs):
        super(OperationEngineManager, self).__init__(*args, **kwargs)
        self.protection_api = protection_api.API()

    def create_scheduled_operation(self, context, request_spec=None):
        LOG.debug("Received a rpc call from a api service."
                  "request_spec:%s", request_spec)
