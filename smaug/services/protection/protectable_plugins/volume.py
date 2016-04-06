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


class VolumeProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """Protectable plugin implementation for volume from cinder.

    """

    _SUPPORT_RESOURCE_TYPE = constants.VOLUME_RESOURCE_TYPE

    @property
    def _client(self):
        if not hasattr(self, '_client_instance'):
            self._client_instance = ClientFactory.create_client(
                "cinder",
                self._context)

        return self._client_instance

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return (constants.SERVER_RESOURCE_TYPE,
                constants.PROJECT_RESOURCE_TYPE)

    def list_resources(self):
        try:
            volumes = self._client.volumes.list(detailed=False)
        except Exception as e:
            LOG.exception(_LE("List all summary volumes "
                              "from cinder failed."))
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                      id=vol.id, name=vol.name)
                    for vol in volumes]

    def show_resource(self, resource_id):
        try:
            volume = self._client.volumes.get(resource_id)
        except Exception as e:
            LOG.exception(_LE("Show a summary volume "
                              "from cinder failed."))
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                     id=volume.id, name=volume.name)

    def get_dependent_resources(self, parent_resource):
        def _is_attached_to(vol):
            if parent_resource.type == constants.SERVER_RESOURCE_TYPE:
                return any([s.get('server_id') == parent_resource.id
                            for s in vol.attachments])
            if parent_resource.type == constants.PROJECT_RESOURCE_TYPE:
                return getattr(vol, 'os-vol-tenant-attr:tenant_id') == \
                    parent_resource.id

        try:
            volumes = self._client.volumes.list(detailed=True)
        except Exception as e:
            LOG.exception(_LE("List all detailed volumes "
                              "from cinder failed."))
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                      id=vol.id, name=vol.name)
                    for vol in volumes if _is_attached_to(vol)]
