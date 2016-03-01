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

import six

from oslo_log import log as logging
from smaug.common import constants
from smaug import exception
from smaug.i18n import _LE
from smaug import resource
from smaug.services.protection.client_factory import ClientFactory
from smaug.services.protection import protectable_plugin

LOG = logging.getLogger(__name__)


class ServerProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """Protectable plugin implementation for server from nova.

    """

    _SUPPORT_RESOURCE_TYPE = constants.SERVER_RESOURCE_TYPE

    @property
    def _client(self):
        if not hasattr(self, '_client_instance'):
            self._client_instance = ClientFactory.create_client(
                "nova",
                self._context)

        return self._client_instance

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return (constants.PROJECT_RESOURCE_TYPE, )

    def list_resources(self):
        try:
            servers = self._client.servers.list(detailed=False)
        except Exception as e:
            LOG.exception(_LE("List all servers from nova failed."))
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                      id=server.id)
                    for server in servers]

    def get_dependent_resources(self, parent_resource):
        # Utilize list_resource here, cause its function is
        # listing resources of given project
        return self.list_resources()
