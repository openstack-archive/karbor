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
import uuid

from karbor.common import constants
from karbor import exception
from karbor import resource
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protectable_plugin
from oslo_config import cfg
from oslo_log import log as logging


LOG = logging.getLogger(__name__)

pod_protectable_opts = [
    cfg.StrOpt('namespace',
               default='default',
               help='The namespace name that kubernetes client use.')
]


def register_opts(conf):
    conf.register_opts(pod_protectable_opts, group='pod_protectable')


INVALID_POD_STATUS = ['Pending', 'Failed', 'Unknown']


class K8sPodProtectablePlugin(protectable_plugin.ProtectablePlugin):
    """K8s pod protectable plugin"""

    _SUPPORT_RESOURCE_TYPE = constants.POD_RESOURCE_TYPE

    def __init__(self, context=None, config=None):
        super(K8sPodProtectablePlugin, self).__init__(context, config)
        self.namespace = None
        if self._conf:
            register_opts(self._conf)
            plugin_cfg = self._conf.pod_protectable
            self.namespace = plugin_cfg.namespace

    def _client(self, context):
        self._client_instance = ClientFactory.create_client(
            "k8s", context)

        return self._client_instance

    def get_resource_type(self):
        return self._SUPPORT_RESOURCE_TYPE

    def get_parent_resource_types(self):
        return (constants.PROJECT_RESOURCE_TYPE)

    def list_resources(self, context, parameters=None):
        try:
            pods = self._client(context).list_namespaced_pod(self.namespace)
        except Exception as e:
            LOG.exception("List all summary pods from kubernetes failed.")
            raise exception.ListProtectableResourceFailed(
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            return [resource.Resource(
                type=self._SUPPORT_RESOURCE_TYPE,
                id=uuid.uuid5(uuid.NAMESPACE_OID, "%s:%s" % (
                    self.namespace, pod.metadata.name)),
                name="%s:%s" % (self.namespace, pod.metadata.name),
                extra_info={'namespace': self.namespace})
                for pod in pods.items
                if pod.status.phase not in INVALID_POD_STATUS]

    def show_resource(self, context, resource_id, parameters=None):
        try:
            if not parameters:
                raise
            name = parameters.get("name", None)
            if ":" in name:
                pod_namespace, pod_name = name.split(":")
            else:
                pod_namespace = self.namespace
                pod_name = name
            pod = self._client(context).read_namespaced_pod(
                pod_name, pod_namespace)
        except Exception as e:
            LOG.exception("Show a summary pod from kubernetes failed.")
            raise exception.ProtectableResourceNotFound(
                id=resource_id,
                type=self._SUPPORT_RESOURCE_TYPE,
                reason=six.text_type(e))
        else:
            if pod.status.phase in INVALID_POD_STATUS:
                raise exception.ProtectableResourceInvalidStatus(
                    id=resource_id, type=self._SUPPORT_RESOURCE_TYPE,
                    status=pod.status.phase)
            return resource.Resource(
                type=self._SUPPORT_RESOURCE_TYPE,
                id=uuid.uuid5(uuid.NAMESPACE_OID, "%s:%s" % (
                    self.namespace, pod.metadata.name)),
                name="%s:%s" % (pod_namespace, pod.metadata.name),
                extra_info={'namespace': pod_namespace})

    def get_dependent_resources(self, context, parent_resource):
        self.list_resources(context)
