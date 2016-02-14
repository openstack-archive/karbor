# Licensed under the Apache License, Version 2.0 (the "License"); you may
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


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class PluggableProtectionProvider(object):
    def __init__(self):
        super(PluggableProtectionProvider, self).__init__()
        self._bank_plugin = None
        self._plugin_map = {}
        self.checkpoint_collection = None
        # TODO(wangliuan)

    def _load_plugins(self, cfg_file):
        # TODO(wangliuan)
        pass

    def get_checkpoint_collection(self):
        # TODO(wangliuan)
        pass

    def build_task_flow(self, plan):
        # TODO(wangliuan)
        pass


class ProviderRegistry(object):
    def __init__(self):
        super(ProviderRegistry, self).__init__()
        # TODO(wangliuan)

    def load_providers(self, cfg_file):
        # TODO(wangliuan)
        pass

    def list_providers(self, list_option):
        # TODO(wangliuan)
        pass

    def show_provider(self, provider_id):
        # TODO(wangliuan)
        pass
