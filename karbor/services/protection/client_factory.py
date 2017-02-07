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

from keystoneauth1 import service_token
from keystoneauth1 import session as keystone_session

import os
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from karbor.common import karbor_keystone_plugin
from karbor import exception
from karbor.i18n import _LE

LOG = logging.getLogger(__name__)


class ClientFactory(object):
    _factory = None
    _keystone_plugin = None

    @staticmethod
    def _list_clients():
        clients_dir = os.path.join(os.path.dirname(__file__), 'clients')
        if not os.path.isdir(clients_dir):
            LOG.error(_LE('clients directory "%s" not found'), clients_dir)
            return

        for file in os.listdir(clients_dir):
            name, ext = os.path.splitext(file)
            if name != '__init__' and name != 'utils' and ext == '.py':
                LOG.debug('Found client "%s"', name)
                yield '%s.clients.%s' % (__package__, name)

    @classmethod
    def _generate_session(cls, context, service):
        plugin = cls._keystone_plugin
        try:
            auth_plugin = service_token.ServiceTokenAuthWrapper(
                plugin.create_user_auth_plugin(context),
                plugin.service_auth_plugin)
        except Exception:
            return None

        try:
            client_conf = cfg.CONF['%s_client' % service]
            auth_insecure = client_conf['%s_auth_insecure' % service]
            ca_file = client_conf['%s_ca_cert_file' % service]
            verify = False if auth_insecure else (ca_file or True)

        except Exception:
            verify = True

        return keystone_session.Session(auth=auth_plugin, verify=verify)

    @classmethod
    def init(cls):
        cls._keystone_plugin = karbor_keystone_plugin.KarborKeystonePlugin()

        cls._factory = {}
        for module in cls._list_clients():
            module = importutils.import_module(module)
            cls._factory[module.SERVICE] = module

    @classmethod
    def create_client(cls, service, context, conf=cfg.CONF, **kwargs):
        module = cls._factory.get(service)
        if module is None:
            raise exception.KarborException(_('Unknown service(%s)') % service)

        kwargs['keystone_plugin'] = cls._keystone_plugin
        if context:
            kwargs['session'] = cls._generate_session(context, service)
        return module.create(context, conf, **kwargs)


def init():
    ClientFactory.init()
