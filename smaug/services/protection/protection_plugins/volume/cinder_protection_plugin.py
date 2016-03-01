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
from smaug.i18n import _, _LE
from smaug.services.protection.client_factory import ClientFactory
from smaug.services.protection.protection_plugins.base_protection_plugin \
    import BaseProtectionPlugin
from smaug.services.protection.protection_plugins.volume \
    import volume_plugin_cinder_schemas as cinder_schemas

LOG = logging.getLogger(__name__)


class CinderProtectionPlugin(BaseProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.VOLUME_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(CinderProtectionPlugin, self).__init__(config)

    def get_supported_resources_types(self):
        return self._SUPPORT_RESOURCE_TYPES

    def get_options_schema(self):
        return cinder_schemas.OPTIONS_SCHEMA

    def get_restore_schema(self):
        return cinder_schemas.RESTORE_SCHEMA

    def get_saved_info_schema(self):
        return cinder_schemas.SAVED_INFO_SCHEMA

    def get_saved_info(self, metadata_store, resource):
        # TODO(hurong)
        pass

    def _cinder_client(self, cntxt):
        return ClientFactory.create_client("cinder", cntxt)

    def create_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        backup_name = kwargs.get("backup_name")
        resource = resource_node.value
        volume_id = resource.id

        bank_section = checkpoint.get_resource_bank_section(volume_id)

        resource_definition = {"volume_id": volume_id}
        cinder_client = self._cinder_client(cntxt)

        LOG.info(_("creating volume backup, volume_id: %s."), volume_id)
        try:
            bank_section.create_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)

            backup = cinder_client.backups.create(volume_id=volume_id,
                                                  name=backup_name,
                                                  force=True)
            resource_definition["backup_id"] = backup.id
            bank_section.create_object("metadata", resource_definition)

        except Exception as e:
            LOG.error(_LE("create volume backup failed, volume_id: %s."),
                      volume_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=six.text_type(e),
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE
            )

    # TODO(hurong): add sync function to update resource status

    def delete_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        resource_id = resource_node.value.id

        bank_section = checkpoint.get_resource_bank_section(resource_id)
        cinder_client = self._cinder_client(cntxt)

        LOG.info(_("deleting volume backup, volume_id: %s."), resource_id)
        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_DELETING)
            resource_definition = bank_section.get_object("metadata")
            backup_id = resource_definition["backup_id"]
            cinder_client.backups.delete(backup_id)
            bank_section.update_object("metadata", resource_definition)
        except Exception as e:
            LOG.error(_LE("delete volume backup failed, volume_id: %s."),
                      resource_id)
            bank_section.update_object("status",
                                       constants.CHECKPOINT_STATUS_ERROR)

            raise exception.DeleteBackupFailed(
                reason=six.text_type(e),
                resource_id=resource_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE
            )

    def restore_backup(self, **kwargs):
        # TODO(hurong):
        pass
