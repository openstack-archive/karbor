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

from functools import partial

from novaclient import exceptions
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.server \
    import server_plugin_schemas
from karbor.services.protection.protection_plugins import utils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

VOLUME_ATTACHMENT_RESOURCE = 'OS::Cinder::VolumeAttachment'
FLOATING_IP_ASSOCIATION = 'OS::Nova::FloatingIPAssociation'

nova_backup_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Nova backup status'
    ),
]


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
            raise exception.CreateResourceFailed(
                name="Server Backup",
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
            raise exception.DeleteResourceFailed(
                name="Server Backup",
                reason=err,
                resource_id=resource_id,
                resource_type=constants.SERVER_RESOURCE_TYPE)


class VerifyOperation(protection_plugin.Operation):
    def __init__(self):
        super(VerifyOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_server_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(
            original_server_id)
        LOG.info('Verifying the server backup, server_id: %s',
                 original_server_id)

        update_method = partial(
            utils.update_resource_verify_result,
            kwargs.get('verify'), resource.type, original_server_id)

        backup_status = bank_section.get_object("status")

        if backup_status == constants.RESOURCE_STATUS_AVAILABLE:
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = ('The status of server backup status is %s.'
                      % backup_status)
            update_method(backup_status, reason)
            raise exception.VerifyResourceFailed(
                name="Server backup",
                reason=reason,
                resource_id=original_server_id,
                resource_type=resource.type)


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_complete(self, checkpoint, resource, context, parameters, **kwargs):
        original_server_id = resource.id
        LOG.info("Restoring server backup, server_id: %s.", original_server_id)

        update_method = None
        try:
            resource_definition = checkpoint.get_resource_bank_section(
                original_server_id).get_object("metadata")

            nova_client = ClientFactory.create_client("nova", context)
            new_resources = kwargs.get("new_resources")

            # restore server instance
            restore_net_id = parameters.get("restore_net_id", None)
            restore_flavor_id = parameters.get("restore_flavor_id", None)
            if restore_flavor_id:
                resource_definition["server_metadata"]['flavor'] = (
                    restore_flavor_id)
            new_server_id = self._restore_server_instance(
                nova_client, new_resources, original_server_id,
                parameters.get("restore_name", "karbor-restore-server"),
                restore_net_id, resource_definition)

            update_method = partial(utils.update_resource_restore_result,
                                    kwargs.get('restore'), resource.type,
                                    new_server_id)
            update_method(constants.RESOURCE_STATUS_RESTORING)
            self._wait_server_to_active(nova_client, new_server_id)

            # restore volume attachment
            self._restore_volume_attachment(
                nova_client, ClientFactory.create_client("cinder", context),
                new_resources, new_server_id, resource_definition)

            # restore floating ip association
            self._restore_floating_association(
                nova_client, new_server_id, resource_definition)

            new_resources[original_server_id] = new_server_id

            update_method(constants.RESOURCE_STATUS_AVAILABLE)

            LOG.info("Finish restore server, server_id: %s.",
                     original_server_id)

        except Exception as e:
            if update_method:
                update_method(constants.RESOURCE_STATUS_ERROR, str(e))
            LOG.exception("Restore server backup failed, server_id: %s.",
                          original_server_id)
            raise exception.RestoreResourceFailed(
                name="Server Backup",
                reason=e,
                resource_id=original_server_id,
                resource_type=constants.SERVER_RESOURCE_TYPE
            )

    def _restore_server_instance(self, nova_client, new_resources,
                                 original_id, restore_name, restore_net_id,
                                 resource_definition):
        server_metadata = resource_definition["server_metadata"]
        properties = {
            "availability_zone": server_metadata.get("availability_zone"),
            "flavor": server_metadata.get("flavor"),
            "name": restore_name,
            "image": None
        }

        # server boot device
        boot_metadata = resource_definition["boot_metadata"]
        boot_device_type = boot_metadata.get("boot_device_type")
        if boot_device_type == "image":
            properties["image"] = new_resources.get(
                boot_metadata["boot_image_id"])

        elif boot_device_type == "volume":
            properties["block_device_mapping_v2"] = [{
                'uuid': new_resources.get(
                    boot_metadata["boot_volume_id"]),
                'source_type': 'volume',
                'destination_type': 'volume',
                'boot_index': 0,
                'delete_on_termination': False,
            }]
        else:
            reason = "Can not find the boot device of the server."
            LOG.error("Restore server backup failed, (server_id:"
                      "%(server_id)s): %(reason)s.",
                      {'server_id': original_id,
                       'reason': reason})
            raise Exception(reason)

        # server key_name, security_groups, networks
        properties["key_name"] = server_metadata.get("key_name", None)

        if server_metadata.get("security_groups"):
            properties["security_groups"] = [
                security_group["name"]
                for security_group in server_metadata["security_groups"]
            ]

        if restore_net_id is not None:
            properties["nics"] = [{'net-id': restore_net_id}]
        elif server_metadata.get("networks"):
            properties["nics"] = [
                {'net-id': network}
                for network in server_metadata["networks"]
            ]

        properties["userdata"] = None

        try:
            server = nova_client.servers.create(**properties)
        except Exception as ex:
            LOG.error('Error creating server (server_id:%(server_id)s): '
                      '%(reason)s',
                      {'server_id': original_id,
                       'reason': ex})
            raise

        return server.id

    def _restore_volume_attachment(self, nova_client, cinder_client,
                                   new_resources, new_server_id,
                                   resource_definition):
        attach_metadata = resource_definition.get("attach_metadata", {})
        for original_id, attach_metadata_item in attach_metadata.items():
            if attach_metadata_item.get("bootable", None) == "true":
                continue

            volume_id = new_resources.get(original_id)
            try:
                nova_client.volumes.create_server_volume(
                    server_id=new_server_id,
                    volume_id=volume_id,
                    device=attach_metadata_item.get("device", None))

            except Exception as ex:
                LOG.error("Failed to attach volume %(vol)s to server %(srv)s, "
                          "reason: %(err)s",
                          {'vol': volume_id,
                           'srv': new_server_id,
                           'err': ex})
                raise

            self._wait_volume_to_attached(cinder_client, volume_id)

    def _restore_floating_association(self, nova_client, new_server_id,
                                      resource_definition):
        server_metadata = resource_definition["server_metadata"]
        for floating_ip in server_metadata.get("floating_ips", []):
            nova_client.servers.add_floating_ip(
                nova_client.servers.get(new_server_id), floating_ip)

    def _wait_volume_to_attached(self, cinder_client, volume_id):
        def _get_volume_status():
            try:
                return cinder_client.volumes.get(volume_id).status
            except Exception as ex:
                LOG.error('Fetch volume(%(volume_id)s) status failed, '
                          'reason: %(reason)s',
                          {'volume_id': volume_id,
                           'reason': ex})
                return 'ERROR'

        is_success = utils.status_poll(
            _get_volume_status,
            interval=self._interval,
            success_statuses={'in-use', },
            failure_statuses={'ERROR', },
            ignore_statuses={'available', 'attaching'}
        )
        if not is_success:
            raise Exception('Attach the volume to server failed')

    def _wait_server_to_active(self, nova_client, server_id):
        def _get_server_status():
            try:
                server = self._fetch_server(nova_client, server_id)
                return server.status.split('(')[0] if server else 'BUILD'
            except Exception as ex:
                LOG.error('Fetch server(%(server_id)s) failed, '
                          'reason: %(reason)s',
                          {'server_id': server_id,
                           'reason': ex})
                return 'ERROR'

        is_success = utils.status_poll(
            _get_server_status,
            interval=self._interval,
            success_statuses={'ACTIVE', },
            failure_statuses={'ERROR', },
            ignore_statuses={'BUILD', 'HARD_REBOOT', 'PASSWORD', 'REBOOT',
                             'RESCUE', 'RESIZE', 'REVERT_RESIZE', 'SHUTOFF',
                             'SUSPENDED', 'VERIFY_RESIZE'},
        )
        if not is_success:
            raise Exception('The server does not start successfully')

    def _fetch_server(self, nova_client, server_id):
        server = None
        try:
            server = nova_client.servers.get(server_id)
        except exceptions.OverLimit as exc:
            LOG.warning("Received an OverLimit response when "
                        "fetching server (%(id)s) : %(exception)s",
                        {'id': server_id,
                         'exception': exc})
        except exceptions.ClientException as exc:
            if ((getattr(exc, 'http_status', getattr(exc, 'code', None)) in
                 (500, 503))):
                LOG.warning("Received the following exception when "
                            "fetching server (%(id)s) : %(exception)s",
                            {'id': server_id,
                             'exception': exc})
            else:
                raise
        return server


class NovaProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.SERVER_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(NovaProtectionPlugin, self).__init__(config)
        self._config.register_opts(nova_backup_opts,
                                   'nova_backup_protection_plugin')
        self._poll_interval = (
            self._config.nova_backup_protection_plugin.poll_interval)

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
    def get_verify_schema(cls, resources_type):
        return server_plugin_schemas.VERIFY_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        return server_plugin_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation()

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_verify_operation(self, resource):
        return VerifyOperation()

    def get_delete_operation(self, resource):
        return DeleteOperation()
