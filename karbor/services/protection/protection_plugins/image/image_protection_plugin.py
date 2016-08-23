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

import eventlet
import os

from io import BytesIO
from karbor.common import constants
from karbor import exception
from karbor.i18n import _, _LE
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection.protection_plugins.base_protection_plugin \
    import BaseProtectionPlugin
from karbor.services.protection.protection_plugins.image \
    import image_plugin_schemas as image_schemas
from oslo_config import cfg
from oslo_log import log as logging
from time import sleep

protection_opts = [
    cfg.IntOpt('backup_image_object_size',
               default=52428800,
               help='The size in bytes of instance image objects'),
    cfg.IntOpt('retry_attempts',
               default=10)
]

CONF = cfg.CONF
CONF.register_opts(protection_opts)
LOG = logging.getLogger(__name__)


class GlanceProtectionPlugin(BaseProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.IMAGE_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(GlanceProtectionPlugin, self).__init__(config)
        self._tp = eventlet.GreenPool()
        self.data_block_size_bytes = CONF.backup_image_object_size

    def _add_to_threadpool(self, func, *args, **kwargs):
        self._tp.spawn_n(func, *args, **kwargs)

    def get_resource_stats(self, checkpoint, resource_id):
        # Get the status of this resource
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        try:
            status = bank_section.get_object("status")
            return status
        except Exception:
            return "undefined"

    def get_options_schema(self, resources_type):
        return image_schemas.OPTIONS_SCHEMA

    def get_restore_schema(self, resources_type):
        return image_schemas.RESTORE_SCHEMA

    def get_saved_info_schema(self, resources_type):
        return image_schemas.SAVED_INFO_SCHEMA

    def get_saved_info(self, metadata_store, resource):
        pass

    def _glance_client(self, cntxt):
        return ClientFactory.create_client("glance", cntxt)

    def create_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        image_id = resource_node.value.id
        bank_section = checkpoint.get_resource_bank_section(image_id)

        resource_definition = {"resource_id": image_id}
        glance_client = self._glance_client(cntxt)

        LOG.info(_("creating image backup, image_id: %s."), image_id)
        try:
            bank_section.create_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)
            image_info = glance_client.images.get(image_id)
            image_metadata = {
                "disk_format": image_info.disk_format,
                "container_format": image_info.container_format
            }
            resource_definition["image_metadata"] = image_metadata
            resource_definition["backup_id"] = image_id

            bank_section.create_object("metadata", resource_definition)
        except Exception as err:
            LOG.error(_LE("create image backup failed, image_id: %s."),
                      image_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)

        self._add_to_threadpool(self._create_backup, glance_client,
                                bank_section, image_id)

    def _create_backup(self, glance_client, bank_section, image_id):
        try:
            image_info = glance_client.images.get(image_id)

            retry_attempts = CONF.retry_attempts
            while image_info.status != "active" and retry_attempts != 0:
                sleep(60)
                image_info = glance_client.images.get(image_id)
                retry_attempts -= 1

            if retry_attempts == 0:
                raise Exception

            image_response = glance_client.images.data(image_id)
            image_response_data = BytesIO()
            for chunk in image_response:
                image_response_data.write(chunk)
            image_response_data.seek(0, os.SEEK_SET)

            chunks = 0
            while True:
                data = image_response_data.read(self.data_block_size_bytes)
                if data == '':
                    break
                bank_section.create_object("data_" + str(chunks), data)
                chunks += 1

            # update resource_definition backup_status
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info(_("finish backup image, image_id: %s."), image_id)
        except Exception as err:
            # update resource_definition backup_status
            LOG.error(_LE("create image backup failed, image_id: %s."),
                      image_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)

    def restore_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get('node')
        original_image_id = resource_node.value.id
        heat_template = kwargs.get("heat_template")

        name = kwargs.get("restore_name", "karbor-restore-image")
        LOG.info(_("restoring image backup, image_id: %s."),
                 original_image_id)

        glance_client = self._glance_client(cntxt)
        bank_section = checkpoint.get_resource_bank_section(original_image_id)
        try:
            resource_definition = bank_section.get_object('metadata')
            image_metadata = resource_definition['image_metadata']
            objects = [key.split("/")[-1] for key in
                       bank_section.list_objects()]

            # get image_data
            image_data = BytesIO()
            for obj in objects:
                if obj.find("data_") == 0:
                    data = bank_section.get_object(obj)
                    image_data.write(data)
            image_data.seek(0, os.SEEK_SET)
            disk_format = image_metadata["disk_format"]
            container_format = image_metadata["container_format"]
            image = glance_client.images.create(
                disk_format=disk_format,
                container_format=container_format,
                name=name)
            glance_client.images.upload(image.id, image_data)

            image_info = glance_client.images.get(image.id)
            retry_attempts = CONF.retry_attempts
            while image_info.status != "active" and retry_attempts != 0:
                sleep(60)
                image_info = glance_client.images.get(image.id)
                retry_attempts -= 1
            if retry_attempts == 0:
                raise Exception

            heat_template.put_parameter(original_image_id, image.id)
        except Exception as e:
            LOG.error(_LE("restore image backup failed, image_id: %s."),
                      original_image_id)
            raise exception.RestoreBackupFailed(
                reason=e,
                resource_id=original_image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE
            )

    def delete_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        image_id = resource_node.value.id
        bank_section = checkpoint.get_resource_bank_section(image_id)

        LOG.info(_LE("deleting image backup failed, image_id: %s."),
                 image_id)
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
            LOG.error(_LE("delete image backup failed, image_id: %s."),
                      image_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteBackupFailed(
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)

    def get_supported_resources_types(self):
        return self._SUPPORT_RESOURCE_TYPES
