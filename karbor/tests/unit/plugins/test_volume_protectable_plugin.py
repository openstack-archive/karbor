# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from cinderclient.v3 import volumes
from collections import namedtuple
import mock

from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.protectable_plugins.volume \
    import VolumeProtectablePlugin

from kubernetes.client.models.v1_cinder_volume_source \
    import V1CinderVolumeSource
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_persistent_volume import V1PersistentVolume
from kubernetes.client.models.v1_persistent_volume_claim \
    import V1PersistentVolumeClaim
from kubernetes.client.models.v1_persistent_volume_claim_spec \
    import V1PersistentVolumeClaimSpec
from kubernetes.client.models.v1_persistent_volume_claim_status \
    import V1PersistentVolumeClaimStatus
from kubernetes.client.models.v1_persistent_volume_claim_volume_source \
    import V1PersistentVolumeClaimVolumeSource
from kubernetes.client.models.v1_persistent_volume_spec \
    import V1PersistentVolumeSpec

from kubernetes.client.models.v1_pod import V1Pod
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_pod_status import V1PodStatus
from kubernetes.client.models.v1_volume import V1Volume

from karbor.tests import base
from oslo_config import cfg

project_info = namedtuple('project_info', field_names=['id', 'type', 'name'])
vol_info = namedtuple('vol_info', ['id', 'attachments', 'name', 'status',
                                   'availability_zone'])


class VolumeProtectablePluginTest(base.TestCase):
    def setUp(self):
        super(VolumeProtectablePluginTest, self).setUp()
        service_catalog = [
            {'type': 'volumev3',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8776/v3/abcd'}],
             },
        ]
        self._context = RequestContext(user_id='demo',
                                       project_id='abcd',
                                       auth_token='efgh',
                                       service_catalog=service_catalog)

    def test_create_client_by_endpoint(self):
        cfg.CONF.set_default('cinder_endpoint',
                             'http://127.0.0.1:8776/v3',
                             'cinder_client')
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual('volumev3',
                         plugin._client(self._context).client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v3/abcd',
                         plugin._client(self._context).client.management_url)

    def test_create_client_by_catalog(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual('volumev3',
                         plugin._client(self._context).client.service_type)
        self.assertEqual('http://127.0.0.1:8776/v3/abcd',
                         plugin._client(self._context).client.management_url)

    def test_get_resource_type(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertEqual("OS::Cinder::Volume", plugin.get_resource_type())

    def test_get_parent_resource_types(self):
        plugin = VolumeProtectablePlugin(self._context)
        self.assertItemsEqual(("OS::Nova::Server", "OS::Kubernetes::Pod",
                               "OS::Keystone::Project"),
                              plugin.get_parent_resource_types())

    @mock.patch.object(volumes.VolumeManager, 'list')
    def test_list_resources(self, mock_volume_list):
        plugin = VolumeProtectablePlugin(self._context)
        mock_volume_list.return_value = [
            vol_info('123', [], 'name123', 'available', 'az1'),
            vol_info('456', [], 'name456', 'available', 'az1'),
        ]
        self.assertEqual([Resource('OS::Cinder::Volume', '123', 'name123',
                                   {'availability_zone': 'az1'}),
                          Resource('OS::Cinder::Volume', '456', 'name456',
                                   {'availability_zone': 'az1'})],
                         plugin.list_resources(self._context))

    @mock.patch.object(volumes.VolumeManager, 'get')
    def test_show_resource(self, mock_volume_get):
        plugin = VolumeProtectablePlugin(self._context)

        vol_info = namedtuple('vol_info', ['id', 'name', 'status',
                              'availability_zone'])
        mock_volume_get.return_value = vol_info(id='123', name='name123',
                                                status='available',
                                                availability_zone='az1')
        self.assertEqual(Resource('OS::Cinder::Volume', '123', 'name123',
                                  {'availability_zone': 'az1'}),
                         plugin.show_resource(self._context, "123"))

    @mock.patch.object(volumes.VolumeManager, 'list')
    def test_get_server_dependent_resources(self, mock_volume_list):
        plugin = VolumeProtectablePlugin(self._context)

        attached = [{'server_id': 'abcdef', 'name': 'name'}]
        mock_volume_list.return_value = [
            vol_info('123', attached, 'name123', 'available', 'az1'),
            vol_info('456', [], 'name456', 'available', 'az1'),
        ]
        self.assertEqual([Resource('OS::Cinder::Volume', '123', 'name123',
                                   {'availability_zone': 'az1'})],
                         plugin.get_dependent_resources(
                             self._context,
                             Resource("OS::Nova::Server", 'abcdef', 'name',
                                      {'availability_zone': 'az1'})))

    @mock.patch.object(volumes.VolumeManager, 'list')
    def test_get_project_dependent_resources(self, mock_volume_list):
        project = project_info('abcd', constants.PROJECT_RESOURCE_TYPE,
                               'nameabcd')
        plugin = VolumeProtectablePlugin(self._context)

        volumes = [
            mock.Mock(name='Volume', id='123', availability_zone='az1'),
            mock.Mock(name='Volume', id='456', availability_zone='az1'),
        ]
        setattr(volumes[0], 'os-vol-tenant-attr:tenant_id', 'abcd')
        setattr(volumes[1], 'os-vol-tenant-attr:tenant_id', 'efgh')
        setattr(volumes[0], 'name', 'name123')
        setattr(volumes[1], 'name', 'name456')

        mock_volume_list.return_value = volumes
        self.assertEqual(
            [Resource('OS::Cinder::Volume', '123', 'name123',
                      {'availability_zone': 'az1'})],
            plugin.get_dependent_resources(self._context, project))

    @mock.patch.object(volumes.VolumeManager, 'list')
    @mock.patch('kubernetes.client.apis.core_v1_api.'
                'CoreV1Api.read_persistent_volume')
    @mock.patch('kubernetes.client.apis.core_v1_api.'
                'CoreV1Api.read_namespaced_persistent_volume_claim')
    @mock.patch('kubernetes.client.apis.core_v1_api.'
                'CoreV1Api.read_namespaced_pod')
    def test_get_pod_dependent_resources(self, mock_pod_read,
                                         mock_pvc_read,
                                         mock_pv_read,
                                         mock_volume_list):
        plugin = VolumeProtectablePlugin(self._context)

        pod = V1Pod(api_version="v1", kind="Pod",
                    metadata=V1ObjectMeta(
                        name="busybox-test",
                        namespace="default",
                        uid="dd8236e1-8c6c-11e7-9b7a-fa163e18e097"),
                    spec=V1PodSpec(
                        volumes=[V1Volume(
                            name="name123",
                            persistent_volume_claim=(
                                V1PersistentVolumeClaimVolumeSource(
                                    claim_name="cinder-claim1'")))],
                        containers=[]),
                    status=V1PodStatus(phase="Running"))

        pvc = V1PersistentVolumeClaim(
            api_version="v1",
            kind="PersistentVolumeClaim",
            metadata=V1ObjectMeta(
                name="cinder-claim1",
                namespace="default",
                uid="fec036b7-9123-11e7-a930-fa163e18e097"),
            spec=V1PersistentVolumeClaimSpec(
                access_modes=["ReadWriteOnce"],
                volume_name="pvc-fec036b7-9123-11e7-a930-fa163e18e097"),
            status=V1PersistentVolumeClaimStatus(phase="Bound"))

        pv = V1PersistentVolume(
            api_version="v1",
            kind="PersistentVolume",
            metadata=V1ObjectMeta(
                name="pvc-fec036b7-9123-11e7-a930-fa163e18e097",
                namespace="None",
                uid="ff43c217-9123-11e7-a930-fa163e18e097"),
            spec=V1PersistentVolumeSpec(
                cinder=V1CinderVolumeSource(
                    fs_type=None,
                    read_only=None,
                    volume_id="7daedb1d-fc99-4a35-ab1b-b64971271d17"
                )),
            status=V1PersistentVolumeClaimStatus(phase="Bound"))

        volumes = [
            mock.Mock(name='Volume',
                      id='7daedb1d-fc99-4a35-ab1b-b64971271d17',
                      availability_zone='az1'),
            mock.Mock(name='Volume',
                      id='7daedb1d-fc99-4a35-ab1b-b64922441d17',
                      availability_zone='az1'),
        ]
        setattr(volumes[0], 'name', 'name123')
        setattr(volumes[1], 'name', 'name456')

        mock_pod_read.return_value = pod
        mock_pvc_read.return_value = pvc
        mock_pv_read.return_value = pv
        mock_volume_list.return_value = volumes
        self.assertEqual(
            [Resource('OS::Cinder::Volume',
                      '7daedb1d-fc99-4a35-ab1b-b64971271d17',
                      'name123',
                      {'availability_zone': 'az1'})],
            plugin.get_dependent_resources(
                self._context,
                Resource(id="c88b92a8-e8b4-504c-bad4-343d92061871",
                         name="default:busybox-test",
                         type="OS::Kubernetes::Pod")))
