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

from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.clients import k8s  # noqa
from karbor.services.protection.protectable_plugins.pod \
    import K8sPodProtectablePlugin

from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_list import V1PodList
from kubernetes.client.models.v1_pod_status import V1PodStatus

from oslo_config import cfg

from karbor.tests import base
import mock
import uuid


class PodProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(PodProtectablePluginTest, self).setUp()
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=None)

    def test_get_resource_type(self):
        plugin = K8sPodProtectablePlugin(self._context, cfg.CONF)

        self.assertEqual('OS::Kubernetes::Pod', plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = K8sPodProtectablePlugin(self._context, cfg.CONF)
        self.assertEqual(("OS::Keystone::Project"),
                         plugin.get_parent_resource_types())

    @mock.patch('kubernetes.client.apis.core_v1_api.'
                'CoreV1Api.list_namespaced_pod')
    def test_list_resources(self, mock_pod_list):
        plugin = K8sPodProtectablePlugin(self._context, cfg.CONF)

        pod = V1Pod(api_version="v1", kind="Pod",
                    metadata=V1ObjectMeta(
                        name="busybox-test",
                        namespace="default",
                        uid="dd8236e1-8c6c-11e7-9b7a-fa163e18e097"),
                    status=V1PodStatus(phase="Running"))
        pod_list = V1PodList(items=[pod])
        mock_pod_list.return_value = pod_list
        self.assertEqual([
            Resource('OS::Kubernetes::Pod',
                     uuid.uuid5(uuid.NAMESPACE_OID, "default:busybox-test"),
                     'default:busybox-test')],
            plugin.list_resources(self._context))

    @mock.patch('kubernetes.client.apis.core_v1_api.'
                'CoreV1Api.read_namespaced_pod')
    def test_show_resource(self, mock_pod_get):
        plugin = K8sPodProtectablePlugin(self._context, cfg.CONF)

        pod = V1Pod(api_version="v1", kind="Pod",
                    metadata=V1ObjectMeta(
                        name="busybox-test",
                        namespace="default",
                        uid="dd8236e1-8c6c-11e7-9b7a-fa163e18e097"),
                    status=V1PodStatus(phase="Running"))
        mock_pod_get.return_value = pod
        self.assertEqual(Resource(
            'OS::Kubernetes::Pod',
            uuid.uuid5(uuid.NAMESPACE_OID, "default:busybox-test"),
            'default:busybox-test'),
            plugin.show_resource(self._context,
                                 uuid.uuid5(uuid.NAMESPACE_OID,
                                            "default:busybox-test"),
                                 {'name': 'default:busybox-test'})
            )
