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

from functools import partial

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.image \
    import image_plugin_schemas as image_schemas
from karbor.services.protection.protection_plugins import utils
from oslo_config import cfg
from oslo_log import log as logging

image_backup_opts = [
    cfg.IntOpt('backup_image_object_size',
               default=65536*10,
               help='The size in bytes of instance image objects. '
                    'The value must be a multiple of 65536('
                    'the size of image\'s chunk).'),
    cfg.IntOpt('poll_interval', default=10,
               help='Poll interval for image status'),
]

LOG = logging.getLogger(__name__)


def get_image_status(glance_client, image_id):
    LOG.debug('Polling image (image_id: %s)', image_id)
    try:
        image = glance_client.images.get(image_id)
        status = image.get('status')
    except exception.NotFound:
        status = 'not-found'
    LOG.debug('Polled image (image_id: %s) status: %s',
              image_id, status)
    return status


class ProtectOperation(protection_plugin.Operation):
    def __init__(self, backup_image_object_size,
                 poll_interval):
        super(ProtectOperation, self).__init__()
        self._data_block_size_bytes = backup_image_object_size
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        image_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(image_id)

        resource_definition = {"resource_id": image_id}
        glance_client = ClientFactory.create_client('glance', context)
        LOG.info("Creating image backup, image_id: %s.", image_id)
        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)
            image_info = glance_client.images.get(image_id)
            if image_info.status != "active":
                is_success = utils.status_poll(
                    partial(get_image_status, glance_client, image_info.id),
                    interval=self._interval, success_statuses={'active'},
                    ignore_statuses={'queued', 'saving'},
                    failure_statuses={'killed', 'deleted', 'pending_delete',
                                      'deactivated', 'NotFound'}
                )
                if is_success is not True:
                    LOG.error("The status of image (id: %s) is invalid.",
                              image_id)
                    raise exception.CreateResourceFailed(
                        name="Image Backup",
                        reason="The status of image is invalid.",
                        resource_id=image_id,
                        resource_type=constants.IMAGE_RESOURCE_TYPE)

            image_metadata = {
                "disk_format": image_info.disk_format,
                "container_format": image_info.container_format,
                "checksum": image_info.checksum
            }
            resource_definition["image_metadata"] = image_metadata

            bank_section.update_object("metadata", resource_definition)
        except Exception as err:
            LOG.error("Create image backup failed, image_id: %s.", image_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Image Backup",
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)
        self._create_backup(glance_client, bank_section, image_id)

    def _create_backup(self, glance_client, bank_section, image_id):
        try:
            chunks_num = utils.backup_image_to_bank(
                glance_client,
                image_id, bank_section,
                self._data_block_size_bytes
            )

            # Save the chunks_num to metadata
            resource_definition = bank_section.get_object("metadata")
            if resource_definition is not None:
                resource_definition["chunks_num"] = chunks_num
            bank_section.update_object("metadata", resource_definition)

            # Update resource_definition backup_status
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info('Protecting image (id: %s) to bank completed '
                     'successfully', image_id)
        except Exception as err:
            # update resource_definition backup_status
            LOG.exception('Protecting image (id: %s) to bank failed.',
                          image_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Image Backup",
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)


class DeleteOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        image_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(image_id)

        LOG.info("Deleting image backup, image_id: %s.", image_id)
        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_DELETING)
            objects = bank_section.list_objects()
            for obj in objects:
                if obj == "status":
                    continue
                bank_section.delete_object(obj)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_DELETED)
        except Exception as err:
            LOG.error("delete image backup failed, image_id: %s.", image_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Image Backup",
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_image_id = resource.id
        name = parameters.get("restore_name", "karbor-restore-image")
        LOG.info("Restoring image backup, image_id: %s.", original_image_id)

        glance_client = ClientFactory.create_client('glance', context)
        bank_section = checkpoint.get_resource_bank_section(original_image_id)
        image_info = None
        try:
            image_info = utils.restore_image_from_bank(
                glance_client, bank_section, name)

            if image_info.status != "active":
                is_success = utils.status_poll(
                    partial(get_image_status, glance_client, image_info.id),
                    interval=self._interval, success_statuses={'active'},
                    ignore_statuses={'queued', 'saving'},
                    failure_statuses={'killed', 'deleted', 'pending_delete',
                                      'deactivated', 'not-found'}
                )
                if is_success is not True:
                    LOG.error('The status of image is invalid. status:%s',
                              image_info.status)
                    raise exception.RestoreResourceFailed(
                        name="Image Backup",
                        resource_id=image_info.id,
                        resource_type=constants.IMAGE_RESOURCE_TYPE)

            kwargs.get("new_resources")[original_image_id] = image_info.id
        except Exception as e:
            LOG.error("Restore image backup failed, image_id: %s.",
                      original_image_id)
            if image_info is not None and hasattr(image_info, 'id'):
                LOG.info("Delete the failed image, image_id: %s.",
                         image_info.id)
                glance_client.images.delete(image_info.id)
            raise exception.RestoreResourceFailed(
                name="Image Backup",
                reason=e, resource_id=original_image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)
        LOG.info("Finish restoring image backup, image_id: %s.",
                 original_image_id)


class VerifyOperation(protection_plugin.Operation):
    def __init__(self):
        super(VerifyOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_image_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(
            original_image_id)
        LOG.info('Verifying the image backup, server_id: %s',
                 original_image_id)

        update_method = partial(
            utils.update_resource_verify_result,
            kwargs.get('verify'), resource.type, original_image_id)

        backup_status = bank_section.get_object("status")

        if backup_status == constants.RESOURCE_STATUS_AVAILABLE:
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = ('The status of image backup status is %s.'
                      % backup_status)
            update_method(backup_status, reason)
            raise exception.VerifyResourceFailed(
                name="Image backup",
                reason=reason,
                resource_id=original_image_id,
                resource_type=resource.type)


class GlanceProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.IMAGE_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(GlanceProtectionPlugin, self).__init__(config)
        self._config.register_opts(image_backup_opts,
                                   'image_backup_plugin')
        self._plugin_config = self._config.image_backup_plugin
        self._data_block_size_bytes = (
            self._plugin_config.backup_image_object_size)
        self._poll_interval = self._plugin_config.poll_interval

        if self._data_block_size_bytes % 65536 != 0 or (
                self._data_block_size_bytes <= 0):
            raise exception.InvalidParameterValue(
                err="The value of CONF.backup_image_object_size "
                    "is invalid!")

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resources_type):
        return image_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resources_type):
        return image_schemas.RESTORE_SCHEMA

    @classmethod
    def get_verify_schema(cls, resources_type):
        return image_schemas.VERIFY_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resources_type):
        return image_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._data_block_size_bytes,
                                self._poll_interval)

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_verify_operation(self, resource):
        return VerifyOperation()

    def get_delete_operation(self, resource):
        return DeleteOperation()
