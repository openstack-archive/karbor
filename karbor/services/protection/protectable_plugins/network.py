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


class NetworkProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """Protectable plugin implementation for Network from Neutron.

    """

    _SUPPORT_RESOURCE_TYPE = constants.NETWORK_RESOURCE_TYPE

    def _neutron_client(self, cntxt):
        return ClientFactory.create_client('neutron', cntxt)

    def _nova_client(self, cntxt):
        return ClientFactory.create_client('nova', cntxt)

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return (constants.SERVER_RESOURCE_TYPE,
                constants.PROJECT_RESOURCE_TYPE)

    def _get_network_id(self):
        """Set network_id as project_id

        Cause the network plugin include the ports, networks,
        subnets, routes, securitygroups, So make the id for
        the whole plugin-package info, not just like the server
        plugin which have the real server-id for the server.
        """

        network_id = self._context.project_id
        return network_id

    def list_resources(self, context, parameters=None):
        try:
            netclient = self._neutron_client(context)
            networks = netclient.list_networks().get('networks')
        except Exception as e:
            LOG.exception("List all summary networks from neutron failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            if networks:
                return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                          id=self._get_network_id(),
                                          name="Network Topology")]
            return []

    def show_resource(self, context, resource_id, parameters=None):
        try:
            if resource_id != self._get_network_id():
                return None

            netclient = self._neutron_client(context)
            networks = netclient.list_networks().get('networks')
        except Exception as e:
            LOG.exception("List all summary networks from neutron failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            if networks:
                return resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                         id=self._get_network_id(),
                                         name="Network Topology")
            return None

    def _get_dependent_resources_by_server(self,
                                           context,
                                           parent_resource):
        try:
            # get metadata about network from neutron
            net_client = self._neutron_client(context)
            network_infos = net_client.list_networks().get('networks')
            neutron_networks = {network["id"] for network in network_infos}

            # get interface info from server
            nova_networks = set()
            serverid = parent_resource.id
            nova_client = ClientFactory.create_client("nova", context)
            interface_list = nova_client.servers.interface_list(serverid)

            # check net_id in interface
            for iface in interface_list:
                net_id = iface.net_id
                if net_id not in nova_networks:
                    nova_networks.add(net_id)

            # get the exsited networks
            valid_networks = nova_networks.intersection(neutron_networks)
            if valid_networks:
                return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                          id=self._get_network_id(),
                                          name="Network Topology")]
            return []
        except Exception as e:
            LOG.exception("List all interfaces from nova failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))

    def _get_dependent_resources_by_project(self,
                                            context,
                                            parent_resource):
        try:
            tid = parent_resource.id
            netclient = self._neutron_client(context)
            networks = netclient.list_networks(tenant_id=tid).get('networks')

            if networks:
                return [resource.Resource(type=self._SUPPORT_RESOURCE_TYPE,
                                          id=self._get_network_id(),
                                          name="Network Topology")]
            else:
                return []

        except Exception as e:
            LOG.exception("List all summary networks from neutron failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))

    def get_dependent_resources(self, context, parent_resource):
        if parent_resource.type == constants.SERVER_RESOURCE_TYPE:
            return self._get_dependent_resources_by_server(context,
                                                           parent_resource)

        if parent_resource.type == constants.PROJECT_RESOURCE_TYPE:
            return self._get_dependent_resources_by_project(context,
                                                            parent_resource)

        return []
