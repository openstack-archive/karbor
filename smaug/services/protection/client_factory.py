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

from oslo_log import log as logging
from oslo_utils import importutils
from smaug.i18n import _LE

LOG = logging.getLogger(__name__)


class ClientFactory(object):
    _factory = {}

    def __init__(self):
        for module in self._list_clients():
            module = importutils.import_module(module)
            self._factory[module.SERVICE] = module.create

    @staticmethod
    def _list_clients():
        clients_dir = os.path.join(os.path.dirname(__file__), 'clients')
        if not os.path.isdir(clients_dir):
            LOG.error(_LE('clients directory "%s" not found'), clients_dir)
            return

        for file in os.listdir(clients_dir):
            name, ext = os.path.splitext(file)
            if name != '__init__' and ext == '.py':
                LOG.Debug('Found client "%s"', name)
                yield '%s.clients.%s' % (__package__, name)

    @staticmethod
    def create_client(service, context):
        return ClientFactory._factory[service].create(context)

CLIENT_FACTORY = ClientFactory()
