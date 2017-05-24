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

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.server \
    import server_plugin_schemas
from karbor.services.protection.restore_heat import HeatResource
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

VOLUME_ATTACHMENT_RESOURCE = 'OS::Cinder::VolumeAttachment'
FLOATING_IP_ASSOCIATION = 'OS::Nova::FloatingIPAssociation'


class ProtectOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        server_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(server_id)

        nova_client = ClientFactory.create_client("nova", context)
        cinder_client = ClientFactory.create_client("cinder", context)
        neutron_client = ClientFactory.create_client("neutron", context)

        resource_definition = {"resource_id": server_id}

        # get dependent resources
        server_child_nodes = []
        resources = checkpoint.resource_graph
        for resource_node in resources:
            resource = resource_node.value
            if resource.id == server_id:
                server_child_nodes = resource_node.child_nodes

        LOG.info("Creating server backup, server_id: %s. ", server_id)
        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)

            # get attach_metadata about volume
            attach_metadata = {}
            for server_child_node in server_child_nodes:
                child_resource = server_child_node.value
                if child_resource.type == constants.VOLUME_RESOURCE_TYPE:
                    volume = cinder_client.volumes.get(child_resource.id)
                    attachments = getattr(volume, "attachments")
                    for attachment in attachments:
                        if attachment["server_id"] == server_id:
                            attachment["bootable"] = getattr(
                                volume, "bootable")
                            attach_metadata[child_resource.id] = attachment
            resource_definition["attach_metadata"] = attach_metadata

            # get metadata about AZ
            server = nova_client.servers.get(server_id)
            availability_zone = getattr(server, "OS-EXT-AZ:availability_zone")

            # get metadata about network, flavor, key_name, security_groups
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

            # get metadata about boot device
            boot_metadata = {}
            image_info = getattr(server, "image", None)
            if image_info is not None and isinstance(image_info, dict):
                boot_metadata["boot_device_type"] = "image"
                boot_metadata["boot_image_id"] = image_info['id']
            else:
                boot_metadata["boot_device_type"] = "volume"
                volumes_attached = getattr(
                    server, "os-extended-volumes:volumes_attached", [])
                for volume_attached in volumes_attached:
                    volume_id = volume_attached["id"]
                    volume_attach_metadata = attach_metadata.get(
                        volume_id, None)
                    if volume_attach_metadata is not None and (
                            volume_attach_metadata["bootable"] == "true"):
                        boot_metadata["boot_volume_id"] = volume_id
                        boot_metadata["boot_attach_metadata"] = (
                            volume_attach_metadata)
            resource_definition["boot_metadata"] = boot_metadata

            # save all server's metadata
            server_metadata = {"availability_zone": availability_zone,
                               "networks": networks,
                               "floating_ips": floating_ips,
                               "flavor": flavor,
                               "key_name": key_name,
                               "security_groups": security_groups,
                               }
            resource_definition["server_metadata"] = server_metadata
            LOG.info("Creating server backup, resource_definition: %s.",
                     resource_definition)
            bank_section.update_object("metadata", resource_definition)

            # update resource_definition backup_status
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info("Finish backup server, server_id: %s.", server_id)
        except Exception as err:
            # update resource_definition backup_status
            LOG.exception("Create backup failed, server_id: %s.", server_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=server_id,
                resource_type=constants.SERVER_RESOURCE_TYPE)


class DeleteOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)

        LOG.info("deleting server backup, server_id: %s.", resource_id)

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
            LOG.info("finish delete server, server_id: %s.", resource_id)
        except Exception as err:
            # update resource_definition backup_status
            LOG.error("Delete backup failed, server_id: %s.", resource_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteBackupFailed(
                reason=err,
                resource_id=resource_id,
                resource_type=constants.SERVER_RESOURCE_TYPE)


class RestoreOperation(protection_plugin.Operation):
    def on_complete(self, checkpoint, resource, context, parameters, **kwargs):
        original_server_id = resource.id
        heat_template = kwargs.get("heat_template")

        restore_name = parameters.get("restore_name", "karbor-restore-server")

        LOG.info("Restoring server backup, server_id: %s.", original_server_id)

        bank_section = checkpoint.get_resource_bank_section(original_server_id)
        try:
            resource_definition = bank_section.get_object("metadata")

            # restore server instance
            self._heat_restore_server_instance(
                heat_template, original_server_id,
                restore_name, resource_definition)

            # restore volume attachment
            self._heat_restore_volume_attachment(
                heat_template, original_server_id, resource_definition)

            # restore floating ip association
            self._heat_restore_floating_association(
                heat_template, original_server_id, resource_definition)
            LOG.debug("Restoring server backup, heat_template: %s.",
                      heat_template)
            LOG.info("Finish restore server, server_id: %s.",
                     original_server_id)
        except Exception as e:
            LOG.exception("restore server backup failed, server_id: %s.",
                          original_server_id)
            raise exception.RestoreBackupFailed(
                reason=e,
                resource_id=original_server_id,
                resource_type=constants.SERVER_RESOURCE_TYPE
            )

    def _heat_restore_server_instance(self, heat_template,
                                      original_id, restore_name,
                                      resource_definition):
        server_metadata = resource_definition["server_metadata"]
        properties = {
            "availability_zone": server_metadata["availability_zone"],
            "flavor": server_metadata["flavor"],
            "name": restore_name,
        }
        # server boot device
        boot_metadata = resource_definition["boot_metadata"]
        boot_device_type = boot_metadata["boot_device_type"]
        if boot_device_type == "image":
            original_image_id = boot_metadata["boot_image_id"]
            image_id = heat_template.get_resource_reference(
                original_image_id)
            properties["image"] = image_id
        elif boot_device_type == "volume":
            original_volume_id = boot_metadata["boot_volume_id"]
            volume_id = heat_template.get_resource_reference(
                original_volume_id)
            properties["block_device_mapping_v2"] = [{
                "volume_id": volume_id,
                "delete_on_termination": False,
                "boot_index": 0,
            }]
        else:
            LOG.exception("Restore server backup failed, server_id: %s.",
                          original_id)
            raise exception.RestoreBackupFailed(
                reason="Can not find the boot device of the server.",
                resource_id=original_id,
                resource_type=constants.SERVER_RESOURCE_TYPE
            )

        # server key_name, security_groups, networks
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

        heat_resource_id = uuidutils.generate_uuid()
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
        for original_id, attach_metadata_item in attach_metadata.items():
            device = attach_metadata_item.get("device", None)
            if attach_metadata_item.get("bootable", None) != "true":
                instance_uuid = heat_template.get_resource_reference(
                    original_server_id)
                volume_id = heat_template.get_resource_reference(
                    original_id)
                properties = {"mountpoint": device,
                              "instance_uuid": instance_uuid,
                              "volume_id": volume_id}
                heat_resource_id = uuidutils.generate_uuid()
                heat_attachment_resource = HeatResource(
                    heat_resource_id,
                    VOLUME_ATTACHMENT_RESOURCE)
                for key, value in properties.items():
                    heat_attachment_resource.set_property(key, value)
                heat_template.put_resource(
                    "%s_%s" % (original_server_id, original_id),
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
            heat_resource_id = uuidutils.generate_uuid()
            heat_floating_resource = HeatResource(
                heat_resource_id, FLOATING_IP_ASSOCIATION)

            for key, value in properties.items():
                heat_floating_resource.set_property(key, value)
            heat_template.put_resource(
                "%s_%s" % (original_server_id, floating_ip),
                heat_floating_resource)


class NovaProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.SERVER_RESOURCE_TYPE]

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resource_type):
        return server_plugin_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resource_type):
        return server_plugin_schemas.RESTORE_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        return server_plugin_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation()

    def get_restore_operation(self, resource):
        return RestoreOperation()

    def get_delete_operation(self, resource):
        return DeleteOperation()
