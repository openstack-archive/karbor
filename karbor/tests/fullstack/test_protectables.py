# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from karbor.common.constants import RESOURCE_TYPES
from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects


class ProtectablesTest(karbor_base.KarborBaseTest):
    """Test Protectables operation """

    def test_protectables_list(self):
        items = self.karbor_client.protectables.list()
        query_types = [item.protectable_type for item in items]
        self.assertItemsEqual(RESOURCE_TYPES, query_types)

    def test_protectables_get(self):
        protectable_type = 'OS::Keystone::Project'
        res = self.karbor_client.protectables.get(protectable_type)
        self.assertEqual(protectable_type, res.name)

        protectable_type = 'OS::Nova::Server'
        res = self.karbor_client.protectables.get(protectable_type)
        self.assertEqual(protectable_type, res.name)

    def test_protectables_list_instances(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        items = self.karbor_client.protectables.list_instances(
            'OS::Cinder::Volume')
        ids = [item.id for item in items]
        self.assertTrue(volume.id in ids)

        server = self.store(objects.Server())
        server.create()
        items = self.karbor_client.protectables.list_instances(
            'OS::Nova::Server')
        ids = [item.id for item in items]
        self.assertTrue(server.id in ids)

    def test_protectables_get_instance(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        instance = self.karbor_client.protectables.get_instance(
            'OS::Cinder::Volume', volume.id)
        self.assertEqual(volume.id, instance.id)

        server = self.store(objects.Server())
        server.create()
        instance = self.karbor_client.protectables.get_instance(
            'OS::Nova::Server', server.id)
        self.assertEqual(server.id, instance.id)

    def test_protectables_get_attach_volume_instance(self):
        server = self.store(objects.Server())
        server.create()

        volume = self.store(objects.Volume())
        volume.create(1)

        server.attach_volume(volume.id)
        volume_item = self.cinder_client.volumes.get(volume.id)
        ins_res = self.karbor_client.protectables.get_instance(
            'OS::Nova::Server', volume_item.attachments[0]["server_id"])
        self.assertTrue(ins_res.dependent_resources)
        self.assertEqual('OS::Cinder::Volume',
                         ins_res.dependent_resources[0]["type"])
        self.assertEqual(volume.id,
                         ins_res.dependent_resources[0]["id"])

    def test_share_protectables_list_instances(self):
        res_list = self.karbor_client.protectables.list_instances(
            'OS::Manila::Share')
        before_num = len(res_list)
        share = self.store(objects.Share())
        share.create("NFS", 1)
        res_list = self.karbor_client.protectables.list_instances(
            'OS::Manila::Share')
        after_num = len(res_list)
        self.assertEqual(1, after_num - before_num)
