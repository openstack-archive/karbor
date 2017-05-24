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
import os

from io import BytesIO
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
        status = glance_client.images.get(image_id)
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
                    raise exception.CreateBackupFailed(
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
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)
        self._create_backup(glance_client, bank_section, image_id)

    def _create_backup(self, glance_client, bank_section, image_id):
        try:
            image_response = glance_client.images.data(image_id,
                                                       do_checksum=True)
            bank_chunk_num = int(self._data_block_size_bytes/65536)
            LOG.debug("Creating image backup, bank_chunk_num: %s.",
                      bank_chunk_num)

            # backup the data of image
            image_chunks_num = 0
            chunks_num = 1
            image_response_data = BytesIO()
            for chunk in image_response:
                image_response_data.write(chunk)
                image_chunks_num += 1
                if image_chunks_num == bank_chunk_num:
                    image_chunks_num = 0
                    image_response_data.seek(0, os.SEEK_SET)
                    data = image_response_data.read(
                        self._data_block_size_bytes)
                    bank_section.update_object("data_" + str(chunks_num), data)
                    image_response_data.truncate(0)
                    image_response_data.seek(0, os.SEEK_SET)
                    chunks_num += 1

            image_response_data.seek(0, os.SEEK_SET)
            data = image_response_data.read()
            if data != '':
                bank_section.update_object("data_" + str(chunks_num), data)

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
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)


class DeleteOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        image_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(image_id)

        LOG.info("Deleting image backup failed, image_id: %s.", image_id)
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
            raise exception.DeleteBackupFailed(
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_image_id = resource.id
        heat_template = kwargs.get("heat_template")

        name = parameters.get("restore_name", "karbor-restore-image")
        LOG.info("Restoring image backup, image_id: %s.", original_image_id)

        glance_client = ClientFactory.create_client('glance', context)
        bank_section = checkpoint.get_resource_bank_section(original_image_id)
        try:
            resource_definition = bank_section.get_object('metadata')
            image_metadata = resource_definition['image_metadata']
            objects = [key.split("/")[-1] for key in
                       bank_section.list_objects()
                       if (key.split("/")[-1]).startswith("data_")]

            # check the chunks_num
            chunks_num = resource_definition.get("chunks_num", 0)
            if len(objects) != int(chunks_num):
                raise exception.RestoreBackupFailed(
                    reason=" The chunks_num of restored image is invalid.",
                    resource_id=original_image_id,
                    resource_type=constants.IMAGE_RESOURCE_TYPE)

            sorted_objects = sorted(objects, key=lambda s: int(s[5:]))
            image_data = ImageBankIO(bank_section, sorted_objects)
            disk_format = image_metadata["disk_format"]
            container_format = image_metadata["container_format"]
            image = glance_client.images.create(
                disk_format=disk_format,
                container_format=container_format,
                name=name)
            glance_client.images.upload(image.id, image_data)

            image_info = glance_client.images.get(image.id)
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
                    raise exception.RestoreBackupFailed(
                        resource_id=image_info.id,
                        resource_type=constants.IMAGE_RESOURCE_TYPE)

            # check the checksum
            if image_info.checksum != image_metadata["checksum"]:
                raise exception.RestoreBackupFailed(
                    reason=" The checksum of restored image is invalid.",
                    resource_id=original_image_id,
                    resource_type=constants.IMAGE_RESOURCE_TYPE)
            heat_template.put_parameter(original_image_id, image.id)
        except Exception as e:
            LOG.error("Restore image backup failed, image_id: %s.",
                      original_image_id)
            raise exception.RestoreBackupFailed(
                reason=e, resource_id=original_image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)
        LOG.info("Finish restoring image backup, image_id: %s.",
                 original_image_id)


class ImageBankIO(object):
        def __init__(self, bank_section, sorted_objects):
            super(ImageBankIO, self).__init__()
            self.bank_section = bank_section
            self.sorted_objects = sorted_objects
            self.obj_size = len(sorted_objects)
            self.length = 0

        def readable(self):
            return True

        def __iter__(self):
            return self

        def read(self, length=None):
            obj_index = self.length
            self.length += 1
            if self.length > self.obj_size:
                return ''
            return self.bank_section.get_object(
                self.sorted_objects[obj_index])


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

    def get_delete_operation(self, resource):
        return DeleteOperation()
