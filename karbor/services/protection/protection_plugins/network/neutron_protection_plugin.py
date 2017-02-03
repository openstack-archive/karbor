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
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.network \
    import network_plugin_schemas
from karbor.services.protection.restore_heat import HeatResource
from oslo_log import log as logging
from uuid import uuid4

LOG = logging.getLogger(__name__)


def get_network_id(cntxt):
    network_id = cntxt.project_id
    return network_id


class ProtectOperation(protection_plugin.Operation):
    _SUPPORT_RESOURCE_TYPES = [constants.NETWORK_RESOURCE_TYPE]

    def _get_resources_by_network(self, cntxt, neutron_client):
        try:
            networks = neutron_client.list_networks().get('networks')
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
        else:
            return []

    def _get_resources_by_subnet(self, cntxt, neutron_client):
        try:
            subnets = neutron_client.list_subnets().get('subnets')
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
        else:
            return []

    def _get_resources_by_port(self, cntxt, neutron_client):
        try:
            ports = neutron_client.list_ports().get('ports')
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
        else:
            return []

    def _get_resources_by_router(self, cntxt, neutron_client):
        try:
            routers = neutron_client.list_routers().get('routers')
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
        else:
            return []

    def _get_resources_by_security_group(self, cntxt, neutron_client):
        try:
            sgs = neutron_client.list_security_groups().get('security_groups')
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
        else:
            return []

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
            raise exception.CreateBackupFailed(
                reason=err,
                resource_id=network_id,
                resource_type=self._SUPPORT_RESOURCE_TYPES)


class RestoreOperation(protection_plugin.Operation):
    def _heat_restore_networks(self, heat_template, nets_meta):
        for net_meta in nets_meta:
            net_data = nets_meta[net_meta]
            if net_data["router:external"]:
                continue
            heat_resource_id = net_data["name"]
            net_heat_resource = HeatResource(heat_resource_id,
                                             constants.NET_RESOURCE_TYPE)
            properties = {}
            properties["admin_state_up"] = net_data["admin_state_up"]
            properties["port_security_enabled"] = (
                net_data["port_security_enabled"])
            properties["shared"] = net_data["shared"]
            properties["name"] = net_data["name"]

            for key, value in properties.items():
                net_heat_resource.set_property(key, value)
            heat_template.put_resource(heat_resource_id, net_heat_resource)

    def _get_dependent_net(self, network_id, nets_meta):
        for net_meta in nets_meta:
            net_data = nets_meta[net_meta]
            if network_id == net_data["id"]:
                return net_data["name"]

    def _is_external_subnet(self, network_id, nets_meta):
        for net_meta in nets_meta:
            net_data = nets_meta[net_meta]
            if network_id == net_data["id"]:
                return net_data["router:external"]

    def _heat_restore_subnets(self, heat_template, nets_meta, subs_meta):
        for sub_meta in subs_meta:
            sub_data = subs_meta[sub_meta]

            is_ext_subnet = self._is_external_subnet(sub_data["network_id"],
                                                     nets_meta)

            if is_ext_subnet:
                continue

            heat_resource_id = sub_data["name"]
            sub_heat_resource = HeatResource(heat_resource_id,
                                             constants.SUBNET_RESOURCE_TYPE)
            properties = {}
            properties["cidr"] = sub_data["cidr"]
            properties["allocation_pools"] = sub_data["allocation_pools"]
            properties["dns_nameservers"] = sub_data["dns_nameservers"]
            properties["enable_dhcp"] = sub_data["enable_dhcp"]
            properties["gateway_ip"] = sub_data["gateway_ip"]
            properties["host_routes"] = sub_data["host_routes"]
            properties["name"] = sub_data["name"]
            properties["ip_version"] = sub_data["ip_version"]
            net_name = self._get_dependent_net(sub_data["network_id"],
                                               nets_meta)
            properties["network_id"] = (
                heat_template.get_resource_reference(net_name))
            properties["tenant_id"] = sub_data["tenant_id"]

            for key, value in properties.items():
                sub_heat_resource.set_property(key, value)
            heat_template.put_resource(heat_resource_id, sub_heat_resource)

    def _get_subnet_by_subnetid(self, subnet_id, subs_meta):
        for sub_meta in subs_meta:
            sub_data = subs_meta[sub_meta]
            if subnet_id == sub_data["id"]:
                return sub_data["name"]

        return ""

    def _get_new_fixed_ips(self, heat_template, subs_meta, fixed_ips_meta):
        new_fixed_ips = []
        for fixed_ip in fixed_ips_meta:
            properties = {}
            properties["ip_address"] = fixed_ip["ip_address"]
            subnet_name = self._get_subnet_by_subnetid(fixed_ip["subnet_id"],
                                                       subs_meta)
            properties["subnet_id"] = (
                heat_template.get_resource_reference(subnet_name))
            new_fixed_ips.append(properties)

        return new_fixed_ips

    def _heat_restore_ports(self, heat_template,
                            nets_meta, subs_meta, ports_meta):
        for port_meta in ports_meta:
            port_data = ports_meta[port_meta]
            heat_resource_id = port_data["name"]
            port_heat_resource = HeatResource(heat_resource_id,
                                              constants.PORT_RESOURCE_TYPE)

            if (port_data["device_owner"] == "network:router_interface") or (
                    port_data["device_owner"] == "network:router_gateway") or (
                    port_data["device_owner"] == "network:dhcp") or (
                    port_data["device_owner"] == "network:floatingip"):
                continue

            properties = {}
            properties["admin_state_up"] = port_data["admin_state_up"]
            properties["allowed_address_pairs"] = (
                port_data["allowed_address_pairs"])
            properties["device_id"] = port_data["device_id"]
            properties["device_owner"] = port_data["device_owner"]
            new_fixed_ips = self._get_new_fixed_ips(heat_template,
                                                    subs_meta,
                                                    port_data["fixed_ips"])
            properties["fixed_ips"] = new_fixed_ips
            properties["mac_address"] = port_data["mac_address"]
            properties["name"] = port_data["name"]
            net_name = self._get_dependent_net(port_data["network_id"],
                                               nets_meta)
            properties["network_id"] = (
                heat_template.get_resource_reference(net_name))
            properties["port_security_enabled"] = (
                port_data["port_security_enabled"])
            properties["security_groups"] = port_data["security_groups"]

            for key, value in properties.items():
                port_heat_resource.set_property(key, value)
            heat_template.put_resource(heat_resource_id, port_heat_resource)

    def _get_new_external_gateway(self, public_network_id,
                                  gateway_info, subs_meta, neutron_client):
        new_ext_gw = {}

        # get public network id
        if not public_network_id:
            networks = neutron_client.list_networks().get('networks')
            for network in networks:
                if network['router:external'] is True:
                    public_network_id = network['id']
                    break

        new_ext_gw["network"] = public_network_id
        new_ext_gw["enable_snat"] = gateway_info["enable_snat"]
        return new_ext_gw

    def _heat_restore_routers(self, public_network_id, heat_template,
                              subs_meta, routers_meta, neutron_client):
        for router_meta in routers_meta:
            router_data = routers_meta[router_meta]
            heat_resource_id = router_data["name"]
            router_heat_resource = HeatResource(heat_resource_id,
                                                constants.ROUTER_RESOURCE_TYPE)
            properties = {}
            org_external_gateway = router_data["external_gateway_info"]
            new_external_gateway = (
                self._get_new_external_gateway(public_network_id,
                                               org_external_gateway,
                                               subs_meta,
                                               neutron_client))
            properties["external_gateway_info"] = new_external_gateway
            properties["name"] = router_data["name"]

            for key, value in properties.items():
                router_heat_resource.set_property(key, value)
            heat_template.put_resource(heat_resource_id, router_heat_resource)

    def _get_router_name(self, device_id, routers_meta):
        for router_meta in routers_meta:
            router_data = routers_meta[router_meta]
            if device_id == router_data["id"]:
                return router_data["name"]

        return ""

    def _get_subnet_name_by_fixed_ips(self, fixed_ips, subs_meta):
        subnet_id = fixed_ips[0]["subnet_id"]
        for sub_meta in subs_meta:
            sub_data = subs_meta[sub_meta]
            if subnet_id == sub_data["id"]:
                return sub_data["name"]

        return ""

    def _heat_restore_routerinterfaces(self, heat_template,
                                       subs_meta, routers_meta, ports_meta):
        for port_meta in ports_meta:
            port_data = ports_meta[port_meta]
            heat_resource_id = str(uuid4())
            port_heat_resource = (
                HeatResource(heat_resource_id,
                             constants.ROUTERINTERFACE_RESOURCE_TYPE))

            if port_data["device_owner"] != "network:router_interface":
                continue

            properties = {}
            router_name = self._get_router_name(port_data["device_id"],
                                                routers_meta)
            properties["router"] = (
                heat_template.get_resource_reference(router_name))
            subnet_name = (
                self._get_subnet_name_by_fixed_ips(port_data["fixed_ips"],
                                                   subs_meta))
            properties["subnet"] = (
                heat_template.get_resource_reference(subnet_name))

            for key, value in properties.items():
                port_heat_resource.set_property(key, value)
            heat_template.put_resource(heat_resource_id, port_heat_resource)

    def _get_security_group_rules(self, security_group_rules):
        new_security_group_rules = []
        for sg in security_group_rules:
            if sg["remote_ip_prefix"] is None:
                continue

            security_group_rule = {}
            security_group_rule["direction"] = sg["direction"]
            security_group_rule["ethertype"] = sg["ethertype"]
            security_group_rule["port_range_max"] = sg["port_range_max"]
            security_group_rule["port_range_min"] = sg["port_range_min"]
            security_group_rule["protocol"] = sg["protocol"]
            security_group_rule["remote_group_id"] = sg["remote_group_id"]
            security_group_rule["remote_ip_prefix"] = sg["remote_ip_prefix"]

            if "remote_mode" in sg:
                security_group_rule["remote_mode"] = sg["remote_mode"]
            new_security_group_rules.append(security_group_rule)

        return new_security_group_rules

    def _heat_restore_securitygroups(self, heat_template, sgs_meta):
        for sg_meta in sgs_meta:
            sg_data = sgs_meta[sg_meta]

            # Skip the default securitygroups
            if sg_data["name"] == "default":
                continue

            heat_resource_id = sg_data["name"]
            sg_heat_resource = (
                HeatResource(heat_resource_id,
                             constants.SECURITYGROUP_RESOURCE_TYPE))
            properties = {}
            sg_rules = sg_data["security_group_rules"]
            properties["description"] = sg_data["description"]
            properties["name"] = sg_data["name"]
            properties["rules"] = self._get_security_group_rules(sg_rules)

            for key, value in properties.items():
                sg_heat_resource.set_property(key, value)
            heat_template.put_resource(heat_resource_id, sg_heat_resource)

    def on_main(self, checkpoint, resource, context,
                parameters, heat_template, **kwargs):
        neutron_client = ClientFactory.create_client("neutron", context)
        network_id = get_network_id(context)
        public_network_id = parameters.get("public_network_id")
        bank_section = checkpoint.get_resource_bank_section(network_id)

        try:
            resource_definition = bank_section.get_object("metadata")

            # Config Net
            if "network_metadata" in resource_definition:
                nets_meta = resource_definition["network_metadata"]
                self._heat_restore_networks(heat_template, nets_meta)

            # Config Subnet
            if "subnet_metadata" in resource_definition:
                subs_meta = resource_definition["subnet_metadata"]
                self._heat_restore_subnets(heat_template, nets_meta, subs_meta)

            # Config Port
            if "port_metadata" in resource_definition:
                ports_meta = resource_definition["port_metadata"]
                self._heat_restore_ports(heat_template, nets_meta,
                                         subs_meta, ports_meta)

            # Config Router
            if "router_metadata" in resource_definition:
                routers_meta = resource_definition["router_metadata"]
                self._heat_restore_routers(public_network_id,
                                           heat_template,
                                           subs_meta,
                                           routers_meta,
                                           neutron_client)

            # Config RouterInterface
            if [subs_meta is not None] and (
                    [routers_meta is not None] and [ports_meta is not None]):
                self._heat_restore_routerinterfaces(heat_template, subs_meta,
                                                    routers_meta, ports_meta)

            # Config Securiy-group
            if "security-group_metadata" in resource_definition:
                sgs_meta = resource_definition["security-group_metadata"]
                self._heat_restore_securitygroups(heat_template, sgs_meta)

        except Exception as e:
            LOG.error("restore network backup failed, network_id: %s.",
                      network_id)
            raise exception.RestoreBackupFailed(
                reason=six.text_type(e),
                resource_id=network_id,
                resource_type=constants.NETWORK_RESOURCE_TYPE
            )


class NeutronProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.NETWORK_RESOURCE_TYPE]

    @classmethod
    def get_supported_resources_types(self):
        return self._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(self, resources_type):
        return network_plugin_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(self, resources_type):
        return network_plugin_schemas.RESTORE_SCHEMA

    @classmethod
    def get_saved_info_schema(self, resources_type):
        return network_plugin_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(self, metadata_store, resource):
        # TODO(chenhuayi)
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation()

    def get_restore_operation(self, resource):
        return RestoreOperation()

    def get_delete_operation(self, resource):
        # TODO(chenhuayi)
        pass
