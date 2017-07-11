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

INVALID_INSTANCE_STATUS = ['BUILD', 'REBOOT', 'RESIZE', 'ERROR']


class DatabaseInstanceProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """Trove database instances protectable plugin"""

    _SUPPORT_RESOURCE_TYPE = constants.DATABASE_RESOURCE_TYPE

    def _client(self, context):
        self._client_instance = ClientFactory.create_client(
            "trove",
            context)

        return self._client_instance

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return (constants.PROJECT_RESOURCE_TYPE, )

    def list_resources(self, context, parameters=None):
        try:
            instances = self._client(context).instances.list()
        except Exception as e:
            LOG.exception("List all database instances from trove failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                      id=instance.id, name=instance.name)
                    for instance in instances
                    if instance.status not in INVALID_INSTANCE_STATUS]

    def show_resource(self, context, resource_id, parameters=None):
        try:
            instance = self._client(context).instances.get(resource_id)
        except Exception as e:
            LOG.exception("Show a database instance from trove failed.")
            raise exception.ProtectableResourceNotFound(
                id=resource_id,
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            if instance.status in INVALID_INSTANCE_STATUS:
                raise exception.ProtectableResourceInvalidStatus(
                    id=resource_id, type=self._SUPPORT_RESOURCE_TYPE,
                    status=instance.status)
            return resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                     id=instance.id, name=instance.name)

    def get_dependent_resources(self, context, parent_resource):
        try:
            instances = self._client(context).instances.list()
        except Exception as e:
            LOG.exception("List all database instances from trove failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                      id=instance.id,
                                      name=instance.name)
                    for instance in instances
                    if instance.project_id == parent_resource.id
                    and instance.status not in INVALID_INSTANCE_STATUS]
