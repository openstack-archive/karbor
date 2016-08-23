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

import eventlet
from io import BytesIO
import os
from time import sleep
from uuid import uuid4

from karbor.common import constants
from karbor import exception
from karbor.i18n import _, _LE
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection.protection_plugins.base_protection_plugin \
    import BaseProtectionPlugin
from karbor.services.protection.protection_plugins.server \
    import server_plugin_schemas
from karbor.services.protection.restore_heat import HeatResource
from oslo_config import cfg
from oslo_log import log as logging

protection_opts = [
    cfg.IntOpt('backup_image_object_size',
               default=52428800,
               help='The size in bytes of instance image objects')
]

CONF = cfg.CONF
CONF.register_opts(protection_opts)
LOG = logging.getLogger(__name__)

VOLUME_ATTACHMENT_RESOURCE = 'OS::Cinder::VolumeAttachment'
FLOATING_IP_ASSOCIATION = 'OS::Nova::FloatingIPAssociation'


class NovaProtectionPlugin(BaseProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.SERVER_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(NovaProtectionPlugin, self).__init__(config)
        self._tp = eventlet.GreenPool()
        self.image_object_size = CONF.backup_image_object_size

    def _add_to_threadpool(self, func, *args, **kwargs):
        self._tp.spawn_n(func, *args, **kwargs)

    def get_options_schema(self, resource_type):
        return server_plugin_schemas.OPTIONS_SCHEMA

    def get_restore_schema(self, resource_type):
        return server_plugin_schemas.RESTORE_SCHEMA

    def get_saved_info_schema(self, resource_type):
        return server_plugin_schemas.SAVED_INFO_SCHEMA

    def get_saved_info(self, metadata_store, resource):
        # TODO(luobin)
        pass

    def _glance_client(self, cntxt):
        return ClientFactory.create_client("glance", cntxt)

    def _nova_client(self, cntxt):
        return ClientFactory.create_client("nova", cntxt)

    def _cinder_client(self, cntxt):
        return ClientFactory.create_client("cinder", cntxt)

    def _neutron_client(self, cntxt):
        return ClientFactory.create_client("neutron", cntxt)

    def create_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        server_id = resource_node.value.id

        bank_section = checkpoint.get_resource_bank_section(server_id)

        nova_client = self._nova_client(cntxt)
        glance_client = self._glance_client(cntxt)
        cinder_client = self._cinder_client(cntxt)
        neutron_client = self._neutron_client(cntxt)

        resource_definition = {"resource_id": server_id}
        child_nodes = resource_node.child_nodes
        attach_metadata = {}

        LOG.info(_("creating server backup, server_id: %s."), server_id)

        try:
            bank_section.create_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)

            for child_node in child_nodes:
                child_resource = child_node.value
                if child_resource.type == constants.VOLUME_RESOURCE_TYPE:
                    volume = cinder_client.volumes.get(child_resource.id)
                    attachments = getattr(volume, "attachments")
                    for attachment in attachments:
                        if attachment["server_id"] == server_id:
                            attach_metadata[child_resource.id] = attachment[
                                "device"]
            resource_definition["attach_metadata"] = attach_metadata

            server = nova_client.servers.get(server_id)
            availability_zone = getattr(server, "OS-EXT-AZ:availability_zone")

            addresses = getattr(server, "addresses")
            networks = []
            floating_ips = []
            for network_infos in addresses.values():
                for network_info in network_infos:
                    addr = network_info.get("addr")
                    mac = network_info.get("OS-EXT-IPS-MAC:mac_addr")
                    network_type = network_info.get("OS-EXT-IPS:type")
                    if network_type == 'fixed':
                        port = neutron_client.list_ports(
                            mac_address=mac)["ports"][0]
                        if port["network_id"] not in networks:
                            networks.append(port["network_id"])
                    elif network_type == "floating":
                        floating_ips.append(addr)

            flavor = getattr(server, "flavor")["id"]
            key_name = getattr(server, "key_name", None)
            security_groups = getattr(server, "security_groups", None)

            server_metadata = {"availability_zone": availability_zone,
                               "networks": networks,
                               "floating_ips": floating_ips,
                               "flavor": flavor,
                               "key_name": key_name,
                               "security_groups": security_groups
                               }
            resource_definition["server_metadata"] = server_metadata

            snapshot_id = nova_client.servers.create_image(
                server_id, "snapshot_%s" % server_id)

            bank_section.create_object("metadata", resource_definition)
        except Exception as err:
            # update resource_definition backup_status
            LOG.error(_LE("create backup failed, server_id: %s."), server_id)
            bank_section.create_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=server_id,
                resource_type=constants.SERVER_RESOURCE_TYPE)

        self._add_to_threadpool(self._create_backup, glance_client,
                                bank_section, server_id, snapshot_id,
                                resource_definition, checkpoint)

    def _create_backup(self, glance_client, bank_section, server_id,
                       snapshot_id, resource_definition, checkpoint):
        try:
            image = glance_client.images.get(snapshot_id)
            # TODO(luobin): config retry_attempts
            retry_attempts = 10
            while image.status == "queued" and retry_attempts != 0:
                sleep(60)
                image = glance_client.images.get(snapshot_id)
                retry_attempts -= 1
            if retry_attempts == 0:
                raise Exception

            resource_definition["snapshot_id"] = snapshot_id
            snapshot_metadata = {
                "disk_format": image.disk_format,
                "container_format": image.container_format,
                "name": "snapshot_%s@%s" % (checkpoint.id, server_id)
            }

            if getattr(image, "kernel_id", None) is not None:
                kernel = glance_client.images.get(image.kernel_id)
                kernel_metadata = {
                    "disk_format": kernel.disk_format,
                    "container_format": kernel.container_format,
                    "name": "kernel_%s@%s" % (checkpoint.id, server_id)
                }
                snapshot_metadata["kernel_metadata"] = kernel_metadata

            if getattr(image, "ramdisk_id", None) is not None:
                ramdisk = glance_client.images.get(image.ramdisk_id)
                ramdisk_metadata = {
                    "disk_format": ramdisk.disk_format,
                    "container_format": ramdisk.container_format,
                    "name": "ramdisk_%s@%s" % (checkpoint.id, server_id)
                }
                snapshot_metadata["ramdisk_metadata"] = ramdisk_metadata

            resource_definition["snapshot_metadata"] = snapshot_metadata
            # write resource_definition in bank
            bank_section.create_object("metadata", resource_definition)

            image = glance_client.images.get(snapshot_id)
            # TODO(luobin): config retry_attempts
            retry_attempts = 10
            while image.status != "active" and retry_attempts != 0:
                sleep(60)
                image = glance_client.images.get(snapshot_id)
                retry_attempts -= 1
            if retry_attempts == 0:
                raise Exception

            # store kernel_data if need
            if getattr(image, "kernel_id", None) is not None:
                kernel_id = image.kernel_id
                kernel_response = glance_client.images.data(kernel_id)
                kernel_response_data = BytesIO()
                for chunk in kernel_response:
                    kernel_response_data.write(chunk)
                kernel_response_data.seek(0, os.SEEK_SET)

                chunks = 0
                while True:
                    data = kernel_response_data.read(self.image_object_size)
                    if data == '':
                        break
                    bank_section.create_object("kernel_" + str(chunks), data)
                    chunks += 1

            # store ramdisk_data if need
            if getattr(image, "ramdisk_id", None) is not None:
                ramdisk_id = image.ramdisk_id
                ramdisk_response = glance_client.images.data(ramdisk_id)
                ramdisk_response_data = BytesIO()
                for chunk in ramdisk_response:
                    ramdisk_response_data.write(chunk)
                ramdisk_response_data.seek(0, os.SEEK_SET)

                chunks = 0
                while True:
                    data = ramdisk_response_data.read(self.image_object_size)
                    if data == '':
                        break
                    bank_section.create_object("ramdisk_" + str(chunks), data)
                    chunks += 1

            # store snapshot_data
            image_response = glance_client.images.data(snapshot_id)
            image_response_data = BytesIO()
            for chunk in image_response:
                image_response_data.write(chunk)
            image_response_data.seek(0, os.SEEK_SET)

            chunks = 0
            while True:
                data = image_response_data.read(self.image_object_size)
                if data == '':
                    break
                bank_section.create_object("snapshot_" + str(chunks), data)
                chunks += 1

            glance_client.images.delete(snapshot_id)

            # update resource_definition backup_status
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info(_("finish backup server, server_id: %s."), server_id)
        except Exception as err:
            LOG.error(_LE("create backup failed, server_id: %s."), server_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)

            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=server_id,
                resource_type=constants.SERVER_RESOURCE_TYPE)

    def restore_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        original_server_id = resource_node.value.id
        heat_template = kwargs.get("heat_template")

        restore_name = kwargs.get("restore_name", "karbor-restore-server")

        LOG.info(_("restoring server backup, server_id: %s."),
                 original_server_id)

        bank_section = checkpoint.get_resource_bank_section(original_server_id)
        try:
            resource_definition = bank_section.get_object("metadata")

            # restore server snapshot
            image_id = self._restore_server_snapshot(
                bank_section, checkpoint, cntxt,
                original_server_id, resource_definition)

            # restore server instance
            self._heat_restore_server_instance(
                heat_template, image_id, original_server_id,
                restore_name, resource_definition)

            # restore volume attachment
            self._heat_restore_volume_attachment(
                heat_template, original_server_id, resource_definition)

            # restore floating ip association
            self._heat_restore_floating_association(
                heat_template, original_server_id, resource_definition)

        except Exception as e:
            LOG.error(_LE("restore server backup failed, server_id: %s."),
                      original_server_id)
            raise exception.RestoreBackupFailed(
                reason=e,
                resource_id=original_server_id,
                resource_type=constants.SERVER_RESOURCE_TYPE
            )

    def _restore_server_snapshot(self, bank_section, checkpoint, cntxt,
                                 original_id, resource_definition):
        snapshot_metadata = resource_definition["snapshot_metadata"]

        glance_client = self._glance_client(cntxt)
        objects = [key.split("/")[-1] for key in
                   bank_section.list_objects()]

        # restore kernel if needed
        kernel_id = None
        if snapshot_metadata.get("kernel_metadata") is not None:
            kernel_id = self._restore_image(
                bank_section, checkpoint, glance_client, "kernel",
                snapshot_metadata["kernel_metadata"], objects,
                original_id)

        # restore ramdisk if needed
        ramdisk_id = None
        if snapshot_metadata.get("ramdisk_metadata") is not None:
            ramdisk_id = self._restore_image(
                bank_section, checkpoint, glance_client, "ramdisk",
                snapshot_metadata["ramdisk_metadata"], objects,
                original_id)

        # restore image
        image_id = self._restore_image(
            bank_section, checkpoint, glance_client, "snapshot",
            snapshot_metadata, objects, original_id,
            kernel_id=kernel_id, ramdisk_id=ramdisk_id)

        image_info = glance_client.images.get(image_id)
        retry_attempts = 10
        while image_info.status != "active" and retry_attempts != 0:
            sleep(60)
            image_info = glance_client.images.get(image_id)
            retry_attempts -= 1
        if retry_attempts == 0:
            raise Exception
        return image_id

    def _restore_image(self, bank_section, checkpoint, glance_client,
                       image_format, image_metadata, objects, original_id,
                       **kwargs):
        if image_metadata.get("name") is None:
            name = "%s_%s@%s" % (image_format, checkpoint.id,
                                 original_id)
        else:
            name = image_metadata["name"]
        disk_format = image_metadata["disk_format"]
        container_format = image_metadata["container_format"]
        image_data = BytesIO()
        for obj in objects:
            if obj.find("%s_" % image_format) == 0:
                data = bank_section.get_object(obj)
                image_data.write(data)
        image_data.seek(0, os.SEEK_SET)
        image = glance_client.images.create(
            disk_format=disk_format,
            container_format=container_format,
            name=name,
            kernel_id=kwargs.get("kernel_id"),
            ramdisk_id=kwargs.get("ramdisk_id"))
        image_id = image.id
        glance_client.images.upload(image_id, image_data)
        return image_id

    def _heat_restore_server_instance(self, heat_template, image_id,
                                      original_id, restore_name,
                                      resource_definition):
        server_metadata = resource_definition["server_metadata"]
        properties = {
            "availability_zone": server_metadata["availability_zone"],
            "flavor": server_metadata["flavor"],
            "image": image_id,
            "name": restore_name,
        }

        if server_metadata["key_name"] is not None:
            properties["key_name"] = server_metadata["key_name"]

        if server_metadata["security_groups"] is not None:
            security_groups = []
            for security_group in server_metadata["security_groups"]:
                security_groups.append(security_group["name"])
            properties["security_groups"] = security_groups

        networks = []
        for network in server_metadata["networks"]:
            networks.append({"network": network})
        properties["networks"] = networks

        heat_resource_id = str(uuid4())
        heat_server_resource = HeatResource(heat_resource_id,
                                            constants.SERVER_RESOURCE_TYPE)
        for key, value in properties.items():
            heat_server_resource.set_property(key, value)

        heat_template.put_resource(original_id,
                                   heat_server_resource)

    def _heat_restore_volume_attachment(self, heat_template,
                                        original_server_id,
                                        resource_definition):
        attach_metadata = resource_definition["attach_metadata"]
        for original_volume_id, device in attach_metadata.items():
            instance_uuid = heat_template.get_resource_reference(
                original_server_id)
            volume_id = heat_template.get_resource_reference(
                original_volume_id)
            properties = {"mountpoint": device,
                          "instance_uuid": instance_uuid,
                          "volume_id": volume_id}

            heat_resource_id = str(uuid4())
            heat_attachment_resource = HeatResource(
                heat_resource_id,
                VOLUME_ATTACHMENT_RESOURCE)
            for key, value in properties.items():
                heat_attachment_resource.set_property(key, value)
            heat_template.put_resource(
                "%s_%s" % (original_server_id, original_volume_id),
                heat_attachment_resource)

    def _heat_restore_floating_association(self, heat_template,
                                           original_server_id,
                                           resource_definition):
        server_metadata = resource_definition["server_metadata"]
        for floating_ip in server_metadata["floating_ips"]:
            instance_uuid = heat_template.get_resource_reference(
                original_server_id)
            properties = {"instance_uuid": instance_uuid,
                          "floating_ip": floating_ip}
            heat_resource_id = str(uuid4())
            heat_floating_resource = HeatResource(
                heat_resource_id, FLOATING_IP_ASSOCIATION)

            for key, value in properties.items():
                heat_floating_resource.set_property(key, value)
            heat_template.put_resource(
                "%s_%s" % (original_server_id, floating_ip),
                heat_floating_resource)

    def delete_backup(self, cntxt, checkpoint, **kwargs):
        resource_node = kwargs.get("node")
        resource_id = resource_node.value.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)

        LOG.info(_("deleting server backup, server_id: %s."), resource_id)

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
            # update resource_definition backup_status
            LOG.error(_LE("delete backup failed, server_id: %s."), resource_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteBackupFailed(
                reason=err,
                resource_id=resource_id,
                resource_type=constants.SERVER_RESOURCE_TYPE)

    def get_supported_resources_types(self):
        return self._SUPPORT_RESOURCE_TYPES
