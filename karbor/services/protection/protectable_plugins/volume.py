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

from karbor.common import constants
from karbor import exception
from karbor import resource
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protectable_plugin
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

INVALID_VOLUME_STATUS = ['error', 'deleting', 'error_deleting']


class VolumeProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """Cinder volume protectable plugin"""

    _SUPPORT_RESOURCE_TYPE = constants.VOLUME_RESOURCE_TYPE

    def _client(self, context):
        self._client_instance = ClientFactory.create_client(
            "cinder",
            context)

        return self._client_instance

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return (constants.SERVER_RESOURCE_TYPE,
                constants.PROJECT_RESOURCE_TYPE)

    def list_resources(self, context, parameters=None):
        try:
            volumes = self._client(context).volumes.list(detailed=True)
        except Exception as e:
            LOG.exception("List all summary volumes from cinder failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(
                type=self._SUPPORT_RESOURCE_TYPE,
                id=vol.id, name=vol.name,
                extra_info={'availability_zone': vol.availability_zone})
                for vol in volumes
                if vol.status not in INVALID_VOLUME_STATUS]

    def show_resource(self, context, resource_id, parameters=None):
        try:
            volume = self._client(context).volumes.get(resource_id)
        except Exception as e:
            LOG.exception("Show a summary volume from cinder failed.")
            raise exception.ProtectableResourceNotFound(
                id=resource_id,
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            if volume.status in INVALID_VOLUME_STATUS:
                raise exception.ProtectableResourceInvalidStatus(
                    id=resource_id, type=self._SUPPORT_RESOURCE_TYPE,
                    status=volume.status)
            return resource.Resource(
                type=self._SUPPORT_RESOURCE_TYPE,
                id=volume.id, name=volume.name,
                extra_info={'availability_zone': volume.availability_zone})

    def get_dependent_resources(self, context, parent_resource):
        def _is_attached_to(vol):
            if parent_resource.type == constants.SERVER_RESOURCE_TYPE:
                return any([s.get('server_id') == parent_resource.id
                            for s in vol.attachments])
            if parent_resource.type == constants.PROJECT_RESOURCE_TYPE:
                return getattr(
                    vol,
                    'os-vol-tenant-attr:tenant_id'
                ) == parent_resource.id

        try:
            volumes = self._client(context).volumes.list(detailed=True)
        except Exception as e:
            LOG.exception("List all detailed volumes from cinder failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(
                type=self._SUPPORT_RESOURCE_TYPE, id=vol.id, name=vol.name,
                extra_info={'availability_zone': vol.availability_zone})
                for vol in volumes if _is_attached_to(vol)]
