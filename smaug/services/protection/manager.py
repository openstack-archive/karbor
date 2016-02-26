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

    def restore(self, context, restore=None):
        LOG.info(_LI("Starting restore service:restore action"))
        LOG.debug('restore :%s tpye:%s', restore,
                  type(restore))

        # TODO(wangliuan)
        return True

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

    def list_protectable_types(self, context):
        # TODO(zengyingzhe)
        LOG.info(_LI("Starting list protectable types."))

        return_stub = [
            "OS::Keystone::Project",
            "OS::Nova::Server",
            "OS::Glance::Image",
            "OS::Cinder::Volume",
            "OS::Neutron::Topology"
        ]
        return return_stub

    def show_protectable_type(self, context, protectable_type):
        # TODO(zengyingzhe)
        LOG.info(_LI("Starting show protectable "
                     "type. tpye:%s"), protectable_type)
        return_stub = {
            "name": "OS::Nova::Server",
            "dependent_types": [
                "OS::Cinder::Volume",
                "OS::Glance::Image"
            ]
        }

        return return_stub

    def list_protectable_instances(self, context, protectable_type,
                                   marker=None, limit=None, sort_keys=None,
                                   sort_dirs=None, filters=None):
        # TODO(zengyingzhe)
        LOG.info(_LI("Starting list protectable instances. "
                     "tpye:%s"), protectable_type)

        return_stub = [
            {
                "id": "557d0cd2-fd8d-4279-91a5-24763ebc6cbc",
            },
            {
                "id": "557d0cd2-fd8d-4279-91a5-24763ebc6cbc",
            }
        ]
        return return_stub

    def list_protectable_dependents(self, context,
                                    protectable_id,
                                    protectable_type):
        # TODO(zengyingzhe)
        LOG.info(_LI("Starting list protectable dependents."
                     "id:%s."), protectable_id)

        return_stub = [
            {
                "id": "5fad94de-2926-486b-ae73-ff5d3477f80d",
                "type": "OS::Cinder::Volume"
            },
            {
                "id": "5fad94de-2926-486b-ae73-ff5d34775555",
                "type": "OS::Cinder::Volume"
            }
        ]
        return return_stub
