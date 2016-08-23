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

from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects


class ProtectablesTest(karbor_base.KarborBaseTest):
    """Test Protectables operation """

    def test_protectables_get_with_project(self):
        protectable_type = 'OS::Keystone::Project'
        res = self.karbor_client.protectables.get(protectable_type)
        self.assertTrue(len(res.dependent_types))

    def test_protectables_list_instances(self):
        res_list = self.karbor_client.protectables.list_instances(
            'OS::Cinder::Volume')
        before_num = len(res_list)
        volume1 = self.store(objects.Volume())
        volume1.create(1)
        res_list = self.karbor_client.protectables.list_instances(
            'OS::Cinder::Volume')
        after_num = len(res_list)
        self.assertEqual(1, after_num - before_num)

    def test_protectables_get_with_server(self):
        server_list = self.karbor_client.protectables.list_instances(
            'OS::Nova::Server')
        before_num = len(server_list)
        server = self.store(objects.Server())
        server.create()

        server_list = self.karbor_client.protectables.list_instances(
            'OS::Nova::Server')
        after_num = len(server_list)
        self.assertEqual(1, after_num - before_num)

    def test_protectables_get_with_attach_volume(self):
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
