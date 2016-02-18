# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
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
from smaug.common import constants
from smaug.i18n import _LE
from smaug.services.protection import checkpoint
from smaug import utils

provider_opt = [
    cfg.MultiStrOpt('plugin',
                    default='',
                    help='plugins to use for protection'),
    cfg.StrOpt('description',
               default='',
               help='the description of provider'),
    cfg.StrOpt('provider_id',
               default='',
               help='the provider id')
]
CONF = cfg.CONF

LOG = logging.getLogger(__name__)

PROTECTION_NAMESPACE = 'smaug.protections'


class PluggableProtectionProvider(object):
    def __init__(self, provider_id,  provider_name, description,  plugins):
        super(PluggableProtectionProvider, self).__init__()
        self._id = provider_id
        self._name = provider_name
        self._description = description
        self._extended_info_schema = {'options_schema': {},
                                      'restore_schema': {},
                                      'saved_info_schema': {}}
        self.checkpoint_collection = None
        self._bank_plugin = None
        self._plugin_map = {}

        self._load_plugins(plugins=plugins)
        if self._bank_plugin:
            self.checkpoint_collection = checkpoint.CheckpointCollection(
                self._bank_plugin)
        else:
            LOG.error(_LE('Bank plugin not exist,check your configuration'))

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def extended_info_schema(self):
        return self._extended_info_schema

    def _load_plugins(self, plugins):
        for plugin_name in plugins:
            try:
                plugin = utils.load_plugin(PROTECTION_NAMESPACE, plugin_name)
            except Exception:
                LOG.exception(_LE("Load protection plugin: %s failed."),
                              plugin_name)
                raise
            else:
                self._plugin_map[plugin_name] = plugin
                if constants.PLUGIN_BANK in plugin_name.lower():
                    self._bank_plugin = plugin
                if hasattr(plugin, 'get_options_schema'):
                    self._extended_info_schema['options_schema'][plugin_name] \
                        = plugin.get_options_schema()
                if hasattr(plugin, 'get_restore_schema'):
                    self._extended_info_schema['restore_schema'][plugin_name] \
                        = plugin.get_restore_schema()
                if hasattr(plugin, 'get_saved_info_schema'):
                    self._extended_info_schema['saved_info_schema'][plugin_name] \
                        = plugin.get_saved_info_schema()

    def get_checkpoint_collection(self):
        return self.checkpoint_collection

    def build_task_flow(self, ctx):
        # TODO(wangliuan)
        pass


class ProviderRegistry(object):
    def __init__(self):
        super(ProviderRegistry, self).__init__()
        self.providers = {}
        self._load_providers()

    def _load_providers(self):
        """load provider

        smaug.conf example:
        [default]
        enabled_providers=provider1,provider2
        [provider1]
        provider_id='' configured by admin
        plugin=BANK  define in setup.cfg
        plugin=VolumeProtectionPlugin define in setup.cfg
        description='the description of provider1'
        [provider2]
        provider_id='' configured by admin
        plugin=BANK  define in setup.cfg
        plugin=VolumeProtectionPlugin define in setup.cfg
        plugin=ServerProtectionPlugin define in setup.cfg
        description='the description of provider2'
        """
        if CONF.enabled_providers:
            for provider_name in CONF.enabled_providers:
                CONF.register_opts(provider_opt, group=provider_name)
                plugins = getattr(CONF, provider_name).plugin
                description = getattr(CONF, provider_name).description
                provider_id = getattr(CONF, provider_name).provider_id
                if not all([plugins, provider_id]):
                    LOG.error(_LE("Invalid provider:%s,check provider"
                                  " configuration"),
                              provider_name)
                    continue
                try:
                    provider = PluggableProtectionProvider(provider_id,
                                                           provider_name,
                                                           description,
                                                           plugins)
                except Exception:
                    LOG.exception(_LE("Load provider: %s failed."),
                                  provider_name)
                else:
                    self.providers[provider_id] = provider

    def list_providers(self, list_option=None):
        if not list_option:
            return [dict(id=provider.id, name=provider.name,
                         description=provider.description)
                    for provider in self.providers.values()]
        # It seems that we don't need list_option

    def show_provider(self, provider_id):
        return self.providers.get(provider_id, None)
