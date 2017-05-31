# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

from karbor import exception
from karbor.i18n import _
from karbor.services.protection import bank_plugin
from karbor.services.protection.checkpoint import CheckpointCollection
from karbor import utils
from oslo_config import cfg
from oslo_log import log as logging

provider_opts = [
    cfg.MultiStrOpt('plugin',
                    default='',
                    help='plugins to use for protection'),
    cfg.StrOpt('bank',
               default='',
               help='bank plugin to use for storage'),
    cfg.StrOpt('description',
               default='',
               help='the description of provider'),
    cfg.StrOpt('name',
               default='',
               help='the name of provider'),
    cfg.StrOpt('id',
               default='',
               help='the provider id')
]
CONF = cfg.CONF

LOG = logging.getLogger(__name__)

PROTECTION_NAMESPACE = 'karbor.protections'

CONF.register_opt(cfg.StrOpt('provider_config_dir',
                             default='providers.d',
                             help='Configuration directory for providers.'
                                  ' Absolute path, or relative to karbor '
                                  ' configuration directory.'))


class PluggableProtectionProvider(object):
    def __init__(self, provider_config):
        super(PluggableProtectionProvider, self).__init__()
        self._config = provider_config
        self._id = self._config.provider.id
        self._name = self._config.provider.name
        self._description = self._config.provider.description
        self._extended_info_schema = {'options_schema': {},
                                      'restore_schema': {},
                                      'saved_info_schema': {}}
        self.checkpoint_collection = None
        self._bank_plugin = None
        self._plugin_map = {}

        if (hasattr(self._config.provider, 'bank') and
                not self._config.provider.bank):
            raise ImportError(_("Empty bank"))

        self._load_bank(self._config.provider.bank)
        self._bank = bank_plugin.Bank(self._bank_plugin)
        self.checkpoint_collection = CheckpointCollection(
            self._bank)

        if hasattr(self._config.provider, 'plugin'):
            for plugin_name in self._config.provider.plugin:
                if not plugin_name:
                    raise ImportError(_("Empty protection plugin"))
                self._register_plugin(plugin_name)

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

    @property
    def bank(self):
        return self._bank

    @property
    def plugins(self):
        return self._plugin_map

    def load_plugins(self):
        return {
            plugin_type: plugin_class(self._config)
            for plugin_type, plugin_class in self.plugins.items()
        }

    def _load_bank(self, bank_name):
        try:
            plugin = utils.load_plugin(PROTECTION_NAMESPACE, bank_name,
                                       self._config)
        except Exception:
            LOG.exception("Load bank plugin: '%s' failed.", bank_name)
            raise
        else:
            self._bank_plugin = plugin

    def _register_plugin(self, plugin_name):
        try:
            plugin = utils.load_class(PROTECTION_NAMESPACE, plugin_name)
        except Exception:
            LOG.exception("Load protection plugin: '%s' failed.", plugin_name)
            raise
        else:
            for resource in plugin.get_supported_resources_types():
                self._plugin_map[resource] = plugin
                if hasattr(plugin, 'get_options_schema'):
                    self._extended_info_schema['options_schema'][resource] \
                        = plugin.get_options_schema(resource)
                if hasattr(plugin, 'get_restore_schema'):
                    self._extended_info_schema['restore_schema'][resource] \
                        = plugin.get_restore_schema(resource)
                if hasattr(plugin, 'get_saved_info_schema'):
                    self._extended_info_schema['saved_info_schema'][resource] \
                        = plugin.get_saved_info_schema(resource)

    def get_checkpoint_collection(self):
        return self.checkpoint_collection

    def get_checkpoint(self, checkpoint_id):
        return self.get_checkpoint_collection().get(checkpoint_id)

    def list_checkpoints(self, provider_id, limit=None, marker=None,
                         plan_id=None, start_date=None, end_date=None,
                         sort_dir=None):
        checkpoint_collection = self.get_checkpoint_collection()
        return checkpoint_collection.list_ids(
            provider_id=provider_id, limit=limit, marker=marker,
            plan_id=plan_id, start_date=start_date, end_date=end_date,
            sort_dir=sort_dir)


class ProviderRegistry(object):
    def __init__(self):
        super(ProviderRegistry, self).__init__()
        self.providers = {}
        self._load_providers()

    def _load_providers(self):
        """load provider"""
        config_dir = utils.find_config(CONF.provider_config_dir)

        for config_file in os.listdir(config_dir):
            if not config_file.endswith('.conf'):
                continue
            config_path = os.path.abspath(os.path.join(config_dir,
                                                       config_file))
            provider_config = cfg.ConfigOpts()
            provider_config(args=['--config-file=' + config_path])
            provider_config.register_opts(provider_opts, 'provider')
            try:
                provider = PluggableProtectionProvider(provider_config)
            except Exception as e:
                LOG.error("Load provider: %(provider)s failed. "
                          "Reason: %(reason)s",
                          {'provider': provider_config.provider.name,
                           'reason': e})
            else:
                LOG.info('Loaded provider: %s successfully.',
                         provider_config.provider.name)
                self.providers[provider.id] = provider

    def list_providers(self, marker=None, limit=None, sort_keys=None,
                       sort_dirs=None, filters=None):
        # TODO(wangliuan) How to use the list option
        return [dict(id=provider.id, name=provider.name,
                     description=provider.description,
                     extended_info_schema=provider.extended_info_schema)
                for provider in self.providers.values()]

    def show_provider(self, provider_id):
        try:
            return self.providers[provider_id]
        except KeyError:
            raise exception.ProviderNotFound(provider_id=provider_id)
