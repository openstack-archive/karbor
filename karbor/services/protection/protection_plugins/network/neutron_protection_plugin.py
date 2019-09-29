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
import copy
from functools import partial
from neutronclient.common import exceptions
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import six

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.network \
    import network_plugin_schemas
from karbor.services.protection.protection_plugins import utils

LOG = logging.getLogger(__name__)


neutron_backup_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Neutron backup status'
    ),
]


def get_network_id(cntxt):
    network_id = cntxt.project_id
    return network_id


class ProtectOperation(protection_plugin.Operation):
    _SUPPORT_RESOURCE_TYPES = [constants.NETWORK_RESOURCE_TYPE]

    def _get_resources_by_network(self, cntxt, neutron_client):
        try:
            networks = neutron_client.list_networks(
                project_id=cntxt.project_id).get('networks')
            networks_metadata = {}

            allowed_keys = [
                'id',
                'admin_state_up',
                'availability_zone_hints',
                'description',
                'ipv4_address_scope',
                'ipv6_address_scope',
                'mtu',
                'name',
                'port_security_enabled',
                'router:external',
                'shared',
                'status',
                'subnets',
                'tags',
                'tenant_id'
                ]

            for network in networks:
                network_metadata = {
                    k: network[k] for k in network if k in allowed_keys}
                networks_metadata[network["id"]] = network_metadata
            return networks_metadata
        except Exception as e:
            LOG.exception("List all summary networks from neutron failed.")
            raise exception.GetProtectionNetworkSubResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPES,
                reason=six.text_type(e))

    def _get_resources_by_subnet(self, cntxt, neutron_client):
        try:
            subnets = neutron_client.list_subnets(
                project_id=cntxt.project_id).get('subnets')
            subnets_metadata = {}

            allowed_keys = [
                'cidr',
                'allocation_pools',
                'description',
                'dns_nameservers',
                'enable_dhcp',
                'gateway_ip',
                'host_routes',
                'id',
                'ip_version',
                'ipv6_address_mode',
                'ipv6_ra_mode',
                'name',
                'network_id',
                'subnetpool_id',
                'tenant_id'
                ]

            for subnet in subnets:
                subnet_metadata = {
                    k: subnet[k] for k in subnet if k in allowed_keys}
                subnets_metadata[subnet["id"]] = subnet_metadata

            return subnets_metadata
        except Exception as e:
            LOG.exception("List all summary subnets from neutron failed.")
            raise exception.GetProtectionNetworkSubResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPES,
                reason=six.text_type(e))

    def _get_resources_by_port(self, cntxt, neutron_client):
        try:
            ports = neutron_client.list_ports(
                project_id=cntxt.project_id).get('ports')
            ports_metadata = {}

            allowed_keys = [
                'admin_state_up',
                'allowed_address_pairs',
                'description',
                'device_id',
                'device_owner',
                'extra_dhcp_opts',
                'fixed_ips',
                'id',
                'mac_address',
                'name',
                'network_id',
                'port_security_enabled',
                'security_groups',
                'status',
                'tenant_id'
                ]

            for port in ports:
                port_metadata = {
                    k: port[k] for k in port if k in allowed_keys}
                ports_metadata[port["id"]] = port_metadata
            return ports_metadata
        except Exception as e:
            LOG.exception("List all summary ports from neutron failed.")
            raise exception.GetProtectionNetworkSubResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPES,
                reason=six.text_type(e))

    def _get_resources_by_router(self, cntxt, neutron_client):
        try:
            routers = neutron_client.list_routers(
                project_id=cntxt.project_id).get('routers')
            routers_metadata = {}

            allowed_keys = [
                'admin_state_u',
                'availability_zone_hints',
                'description',
                'external_gateway_info',
                'id',
                'name',
                'routes',
                'status'
                ]

            for router in routers:
                router_metadata = {
                    k: router[k] for k in router if k in allowed_keys}
                routers_metadata[router["id"]] = router_metadata

            return routers_metadata
        except Exception as e:
            LOG.exception("List all summary routers from neutron failed.")
            raise exception.GetProtectionNetworkSubResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPES,
                reason=six.text_type(e))

    def _get_resources_by_security_group(self, cntxt, neutron_client):
        try:
            sgs = neutron_client.list_security_groups(
                project_id=cntxt.project_id).get('security_groups')
            sgs_metadata = {}

            allowed_keys = [
                'id',
                'description',
                'name',
                'security_group_rules',
                'tenant_id'
                ]

            for sg in sgs:
                sg_metadata = {k: sg[k] for k in sg if k in allowed_keys}
                sgs_metadata[sg["id"]] = sg_metadata
            return sgs_metadata
        except Exception as e:
            LOG.exception("List all summary security_groups from neutron "
                          "failed.")
            raise exception.GetProtectionNetworkSubResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPES,
                reason=six.text_type(e))

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        network_id = get_network_id(context)
        backup_name = kwargs.get("backup_name", "karbor network backup")
        bank_section = checkpoint.get_resource_bank_section(network_id)
        neutron_client = ClientFactory.create_client("neutron", context)

        resource_definition = {"resource_id": network_id}
        resource_definition["backup_name"] = backup_name
        resource_definition["network_metadata"] = (
            self._get_resources_by_network(context, neutron_client))
        resource_definition["subnet_metadata"] = (
            self._get_resources_by_subnet(context, neutron_client))
        resource_definition["port_metadata"] = (
            self._get_resources_by_port(context, neutron_client))
        resource_definition["router_metadata"] = (
            self._get_resources_by_router(context, neutron_client))
        resource_definition["security-group_metadata"] = (
            self._get_resources_by_security_group(context, neutron_client))

        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)

            # write resource_definition in bank
            bank_section.update_object("metadata", resource_definition)

            # update resource_definition backup_status
            bank_section.update_object("status",
                                       constants.CHECKPOINT_STATUS_AVAILABLE)
            LOG.info("finish backup network, network_id: %s.", network_id)
        except Exception as err:
            # update resource_definition backup_status
            LOG.error("create backup failed, network_id: %s.", network_id)
            bank_section.update_object("status",
                                       constants.CHECKPOINT_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Network Backup",
                reason=err,
                resource_id=network_id,
                resource_type=self._SUPPORT_RESOURCE_TYPES)


class VerifyOperation(protection_plugin.Operation):
    def __init__(self):
        super(VerifyOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        network_id = get_network_id(context)
        bank_section = checkpoint.get_resource_bank_section(
            network_id)
        LOG.info('Verifying the network backup, network_id: %s.',
                 network_id)

        update_method = partial(
            utils.update_resource_verify_result,
            kwargs.get('verify'), resource.type, network_id)

        backup_status = bank_section.get_object("status")

        if backup_status == constants.RESOURCE_STATUS_AVAILABLE:
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = ('The status of network backup status is %s.'
                      % backup_status)
            update_method(backup_status, reason)
            raise exception.VerifyResourceFailed(
                name="Network backup",
                reason=reason,
                resource_id=network_id,
                resource_type=resource.type)


class RestoreOperation(protection_plugin.Operation):

    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def _check_complete(self, neutron_client, resources, resource_type):

        success_statuses = ('ACTIVE', 'DOWN')
        failure_statuses = ('ERROR', 'DEGRADED')
        ignore_statuses = ('BUILD')

        get_resource_func = getattr(neutron_client, "show_%s" % resource_type)

        def _get_resource_status(resource_id):
            return get_resource_func(resource_id)[resource_type]['status']

        def _get_all_resource_status():
            recheck_resources = set()

            for r in resources:
                status = _get_resource_status(r)
                if status in success_statuses:
                    continue
                elif status in failure_statuses:
                    return status
                elif status in ignore_statuses:
                    recheck_resources.add(r)
                else:
                    return status

            if recheck_resources:
                resources.difference_update(recheck_resources)
                return ignore_statuses[0]
            return success_statuses[0]

        return utils.status_poll(_get_all_resource_status, self._interval,
                                 success_statuses, failure_statuses,
                                 ignore_statuses)

    def _restore_networks(self, neutron_client, new_resources, nets_meta):
        net_ids = set()
        for _, net_data in nets_meta.items():
            if net_data["router:external"]:
                continue

            props = {
                "admin_state_up": net_data["admin_state_up"],
                "port_security_enabled": net_data["port_security_enabled"],
                "shared": net_data["shared"],
                "name": net_data["name"]
            }
            net_id = neutron_client.create_network(
                {'network': props})['network']['id']
            new_resources[net_data["name"]] = net_id
            net_ids.add(net_id)

        is_success = self._check_complete(neutron_client, net_ids, 'network')
        if not is_success:
            raise Exception("Create networks failed")

    def _restore_subnets(self, neutron_client, new_resources,
                         nets_meta, subs_meta):
        for _, sub_data in subs_meta.items():
            props = {
                "cidr": sub_data["cidr"],
                "allocation_pools": sub_data["allocation_pools"],
                "dns_nameservers": sub_data["dns_nameservers"],
                "enable_dhcp": sub_data["enable_dhcp"],
                "gateway_ip": sub_data["gateway_ip"] if (
                    sub_data["gateway_ip"] != '') else None,
                "host_routes": sub_data["host_routes"],
                "name": sub_data["name"],
                "ip_version": sub_data["ip_version"],
                "network_id": new_resources.get(
                    nets_meta[sub_data['network_id']]['name']),
                "tenant_id": sub_data["tenant_id"],
            }

            subnet_id = neutron_client.create_subnet(
                {'subnet': props})['subnet']['id']
            new_resources[sub_data["name"]] = subnet_id

    def _get_new_fixed_ips(self, new_resources, subs_meta, fixed_ips_meta):
        new_fixed_ips = []
        for fixed_ip in fixed_ips_meta:
            subnet = subs_meta.get(fixed_ip["subnet_id"])
            if not subnet:
                continue

            props = {
                "ip_address": fixed_ip["ip_address"],
                "subnet_id": new_resources.get(
                    subnet['name'])
            }
            new_fixed_ips.append(props)

        return new_fixed_ips

    def _restore_ports(self, neutron_client, new_resources,
                       nets_meta, subs_meta, ports_meta):
        port_ids = set()
        for _, port_data in ports_meta.items():
            if port_data["device_owner"] in (
                    "network:router_interface", "network:router_gateway",
                    "network:dhcp", "network:floatingip"):
                continue

            props = {
                "admin_state_up": port_data["admin_state_up"],
                "device_id": port_data["device_id"],
                "device_owner": port_data["device_owner"],
                "mac_address": port_data["mac_address"],
                "name": port_data["name"],
                "network_id": new_resources.get(
                    nets_meta[port_data['network_id']]['name']),
                "port_security_enabled": port_data["port_security_enabled"],
            }
            new_fixed_ips = self._get_new_fixed_ips(
                new_resources, subs_meta, port_data["fixed_ips"])
            if new_fixed_ips:
                props["fixed_ips"] = new_fixed_ips

            address_pairs = port_data["allowed_address_pairs"]
            if address_pairs:
                address_pairs = copy.deepcopy(address_pairs)
                for pair in address_pairs:
                    if pair.get("mac_address") is None:
                        pair.pop("mac_address", None)
                props["allowed_address_pairs"] = address_pairs
            else:
                props["allowed_address_pairs"] = []

            security_groups = port_data["security_groups"]
            if security_groups:
                props['security_groups'] = [
                    sg
                    for sg in security_groups
                    if new_resources.get(sg) != 'default'
                ]

            port_id = neutron_client.create_port({'port': props})['port']['id']
            new_resources[port_data["name"]] = port_id
            port_ids.add(port_id)

        is_success = self._check_complete(neutron_client, port_ids, 'port')
        if not is_success:
            raise Exception("Create port failed")

    def _get_new_external_gateway(self, public_network_id, gateway_info,
                                  neutron_client):
        # get public network id
        if not public_network_id:
            networks = neutron_client.list_networks().get('networks')
            for network in networks:
                if network['router:external'] is True:
                    public_network_id = network['id']
                    break
            else:
                return

        gateway = {"network_id": public_network_id}
        if gateway_info.get("enable_snat") is not None:
            gateway["enable_snat"] = gateway_info["enable_snat"]
        return gateway

    def _restore_routers(self, neutron_client, new_resources,
                         public_network_id, routers_meta):
        router_ids = set()
        for _, router_data in routers_meta.items():
            props = {"name": router_data["name"]}
            # If creating router with 'external_gateway_info', then Neutron
            # will refuse to to that, because this operation will need role
            # of Admin, but the curent user should not be the role of that.
            # So, it needs to be refactored here later.
            # new_external_gateway = self._get_new_external_gateway(
            #     public_network_id, router_data["external_gateway_info"],
            #     neutron_client)
            # if new_external_gateway:
            #     props["external_gateway_info"] = new_external_gateway
            router_id = neutron_client.create_router(
                {'router': props})['router']['id']
            new_resources[router_data["name"]] = router_id
            router_ids.add(router_id)

        is_success = self._check_complete(neutron_client, router_ids, 'router')
        if not is_success:
            raise Exception("Create router failed")

    def _restore_routerinterfaces(self, neutron_client, new_resources,
                                  subs_meta, routers_meta, ports_meta):
        for _, port_data in ports_meta.items():
            if port_data["device_owner"] != "network:router_interface":
                continue

            router = routers_meta.get(port_data["device_id"])
            if not router:
                continue

            fixed_ips = port_data["fixed_ips"]
            if not fixed_ips:
                continue
            subnet = subs_meta.get(fixed_ips[0]["subnet_id"])
            if not subnet:
                continue

            neutron_client.add_interface_router(
                new_resources.get(router['name']),
                {
                    'subnet_id': new_resources.get(
                        subnet['name'])
                }
            )

    def _get_security_group_rules(self, security_group_rules):
        new_security_group_rules = []
        for sg in security_group_rules:
            if sg["remote_ip_prefix"] is None:
                continue

            security_group_rule = {
                "direction": sg["direction"],
                "ethertype": sg["ethertype"],
                "port_range_max": sg["port_range_max"],
                "port_range_min": sg["port_range_min"],
                "protocol": sg["protocol"],
                "remote_group_id": sg["remote_group_id"],
                "remote_ip_prefix": sg["remote_ip_prefix"],
            }
            if "remote_mode" in sg:
                security_group_rule["remote_mode"] = sg["remote_mode"]

            new_security_group_rules.append(security_group_rule)

        return new_security_group_rules

    def _create_security_group_rules(self, neutron_client, rules, sg_id):

        @excutils.exception_filter
        def _ignore_not_found(ex):
            if isinstance(ex, (exceptions.NotFound,
                               exceptions.NetworkNotFoundClient,
                               exceptions.PortNotFoundClient)):
                return True
            return (isinstance(ex, exceptions.NeutronClientException) and
                    ex.status_code == 404)

        def _is_egress(rule):
            return rule['direction'] == 'egress'

        def _delete_rules():
            try:
                sec = neutron_client.show_security_group(
                    sg_id)['security_group']
            except Exception as ex:
                _ignore_not_found(ex)
            else:
                for rule in sec['security_group_rules']:
                    if _is_egress(rule):
                        with _ignore_not_found:
                            neutron_client.delete_security_group_rule(
                                rule['id'])

        def _format_rule(rule):
            rule['security_group_id'] = sg_id
            if 'remote_mode' in rule:
                remote_mode = rule.pop('remote_mode')

                if remote_mode == 'remote_group_id':
                    rule['remote_ip_prefix'] = None
                    if not rule.get('remote_group_id'):
                        rule['remote_group_id'] = sg_id
                else:
                    rule['remote_group_id'] = None

            for key in ('port_range_min', 'port_range_max'):
                if rule.get(key) is not None:
                    rule[key] = str(rule[key])

        egress_deleted = False
        for rule in rules:
            if _is_egress(rule) and not egress_deleted:
                # There is at least one egress rule, so delete the default
                # rules which allow all egress traffic
                egress_deleted = True

                _delete_rules()

            _format_rule(rule)

            try:
                neutron_client.create_security_group_rule(
                    {'security_group_rule': rule})
            except Exception as ex:
                if not isinstance(ex, exceptions.Conflict) or (
                        isinstance(ex, exceptions.OverQuotaClient)):
                    raise

    def _restore_securitygroups(self, neutron_client, new_resources, sgs_meta):
        for _, sg_data in sgs_meta.items():
            # Skip the default securitygroups
            if sg_data["name"] == "default":
                continue

            props = {
                "name": sg_data["name"],
                "description": sg_data["description"],
            }
            sg_id = neutron_client.create_security_group(
                {'security_group': props})['security_group']['id']
            new_resources[sg_data["name"]] = sg_id

            rules = self._get_security_group_rules(
                sg_data["security_group_rules"])
            self._create_security_group_rules(neutron_client, rules, sg_id)

    def on_main(self, checkpoint, resource, context,
                parameters, **kwargs):
        neutron_client = ClientFactory.create_client("neutron", context)
        network_id = get_network_id(context)
        public_network_id = parameters.get("public_network_id")
        bank_section = checkpoint.get_resource_bank_section(network_id)
        new_resources = kwargs['new_resources']

        def _filter_resources(resources):
            ids = []
            for obj_id, data in resources.items():
                network = nets_meta.get(data['network_id'])
                if not network or network.get("router:external"):
                    ids.append(obj_id)
            for obj_id in ids:
                resources.pop(obj_id)

        try:
            resource_definition = bank_section.get_object("metadata")

            # Config Net
            nets_meta = resource_definition.get("network_metadata")
            if nets_meta:
                self._restore_networks(neutron_client, new_resources,
                                       nets_meta)

            # Config Securiy-group
            sgs_meta = resource_definition.get("security-group_metadata")
            if sgs_meta:
                self._restore_securitygroups(neutron_client, new_resources,
                                             sgs_meta)

            # Config Subnet
            subs_meta = resource_definition.get("subnet_metadata")
            _filter_resources(subs_meta)
            if subs_meta:
                self._restore_subnets(neutron_client, new_resources,
                                      nets_meta, subs_meta)

            # Config Router
            routers_meta = resource_definition.get("router_metadata")
            if routers_meta:
                self._restore_routers(neutron_client, new_resources,
                                      public_network_id, routers_meta)

            # Config Port
            ports_meta = resource_definition.get("port_metadata")
            _filter_resources(ports_meta)
            if ports_meta:
                self._restore_ports(neutron_client, new_resources, nets_meta,
                                    subs_meta, ports_meta)

            # Config RouterInterface
            if all([i is not None
                    for i in [subs_meta, routers_meta, ports_meta]]):
                self._restore_routerinterfaces(
                    neutron_client, new_resources,
                    subs_meta, routers_meta, ports_meta)

        except Exception as e:
            LOG.error("restore network backup failed, network_id: %s.",
                      network_id)
            raise exception.RestoreResourceFailed(
                name="Network Backup",
                reason=six.text_type(e),
                resource_id=network_id,
                resource_type=constants.NETWORK_RESOURCE_TYPE
            )


class DeleteOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, cntxt, parameters, **kwargs):
        network_id = self._get_network_id(cntxt)
        bank_section = checkpoint.get_resource_bank_section(network_id)

        LOG.info("Deleting network backup, network_id: %s.", network_id)

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
            LOG.error("Delete backup failed, network_id: %s.", network_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Network Backup",
                reason=err,
                resource_id=network_id,
                resource_type=self._SUPPORT_RESOURCE_TYPES)


class NeutronProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.NETWORK_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(NeutronProtectionPlugin, self).__init__(config)
        self._config.register_opts(
            neutron_backup_opts,
            'neutron_backup_protection_plugin')
        plugin_config = self._config.neutron_backup_protection_plugin
        self._poll_interval = plugin_config.poll_interval

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resources_type):
        return network_plugin_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resources_type):
        return network_plugin_schemas.RESTORE_SCHEMA

    @classmethod
    def get_verify_schema(cls, resources_type):
        return network_plugin_schemas.VERIFY_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resources_type):
        return network_plugin_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        # TODO(chenhuayi)
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation()

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_verify_operation(self, resource):
        return VerifyOperation()

    def get_delete_operation(self, resource):
        # TODO(chenhuayi)
        pass
