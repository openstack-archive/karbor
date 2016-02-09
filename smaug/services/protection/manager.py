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
Protection Service
"""

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_utils import importutils

from smaug.i18n import _LI
from smaug import manager

LOG = logging.getLogger(__name__)

protection_manager_opts = [
    cfg.IntOpt('update_protection_stats_interval',
               default=3600,
               help='update protection status interval')
]

CONF = cfg.CONF
CONF.register_opts(protection_manager_opts)


class ProtectionManager(manager.Manager):
    """Smaug Protection Manager."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, service_name=None,
                 *args, **kwargs):
        super(ProtectionManager, self).__init__(*args, **kwargs)
        # TODO(wangliuan)  more params and use profiler.trace_cls
        self.provider_registry = importutils.import_object(
            'smaug.services.protection.provider.ProviderRegistry')
        self.flow_engine = None
        # TODO(wangliuan)

    def init_host(self):
        """Handle initialization if this is a standalone service"""
        # TODO(wangliuan)
        LOG.info(_LI("Starting protection service"))

    # TODO(wangliuan) use flow_engine to implement protect function
    def protect(self, plan):
        """create protection for the given plan

        :param plan: Define that protection plan should be done
        """
        # TODO(wangliuan)
        pass

    def restore(self, checkpoint, **kwargs):
        # TODO(wangliuan)
        pass

    def delete(self, plan):
        # TODO(wangliuan)
        pass

    def start(self, plan):
        # TODO(wangliuan)
        pass

    def suspend(self, plan):
        # TODO(wangliuan)
        pass

    def _update_protection_stats(self, plan):
        """Update protection stats

        use the loopingcall to update protection status(
        interval=CONF.update_protection_stats_interval)
        """
        # TODO(wangliuan)
        pass

    def list_checkpoints(self, list_options):
        # TODO(wangliuan)
        pass

    def show_checkpoint(self, checkpoint_id):
        # TODO(wangliuan)
        pass

    def delete_checkpoint(self, checkpoint_id):
        # TODO(wangliuan)
        pass

    def list_providers(self, list_option):
        # TODO(wangliuan)
        pass

    def show_provider(self, provider_id):
        # TODO(wangliuan)
        pass
