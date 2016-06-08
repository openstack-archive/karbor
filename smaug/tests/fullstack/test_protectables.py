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

from smaug.tests.fullstack import smaug_base
from time import sleep


class ProtectablesTest(smaug_base.SmaugBaseTest):
    """Test Protectables operation """

    def create_nova(self, name, image, flavor, key_name=None):
        nova = self.nova_client.servers.create(name, image, flavor,
                                               key_name=key_name)
        sleep(50)
        return nova

    def delete_nova(self, instance_id):
        self.nova_client.servers.delete(instance_id)
        sleep(50)

    def create_server_volume(self, server_id, volume_id, device=None):
        attach_volume = self.nova_client.volumes.create_server_volume(
            server_id, volume_id, device)
        sleep(85)
        return attach_volume

    def delete_server_volume(self, server_id, volume_id):
        detach_volume = self.nova_client.volumes.delete_server_volume(
            server_id, volume_id)
        sleep(85)
        return detach_volume

    def test_protectables_list(self):
        res = self.smaug_client.protectables.list()
        self.assertTrue(len(res))

    def test_protectables_get_with_project(self):
        protectable_type = 'OS::Keystone::Project'
        res = self.smaug_client.protectables.get(protectable_type)
        self.assertTrue(len(res.dependent_types))

    def test_protectables_list_instances(self):
        res_list = self.smaug_client.protectables.list_instances(
            'OS::Cinder::Volume')
        before_num = len(res_list)
        volume_1 = self.create_volume(1, "volume1-L")
        volume_2 = self.create_volume(1, "volume2-L")
        res = self.smaug_client.protectables.list_instances(
            'OS::Cinder::Volume')
        after_num = len(res)
        self.assertEqual(2, after_num - before_num)
        self.delete_volume(volume_1.id)
        self.delete_volume(volume_2.id)

    def test_protectables_get_with_server(self):
        res_list = self.smaug_client.protectables.list_instances(
            'OS::Nova::Server')
        flavors = self.nova_client.flavors.list()
        images = self.nova_client.images.list()
        ins_before = self.nova_client.servers.list()
        oskey = self.nova_client.keypairs.create("oskeypriv")
        instance = self.create_nova("osinstance",
                                    images[0],
                                    flavors[0],
                                    key_name=oskey.name)
        server_list = self.smaug_client.protectables.list_instances(
            'OS::Nova::Server')
        self.assertEqual(1, len(server_list) - len(res_list))
        ins_list = self.nova_client.servers.list()
        self.assertEqual(1, len(ins_list) - len(ins_before))
        self.nova_client.keypairs.delete(oskey.name)
        self.delete_nova(instance.id)

    def test_protectables_get_with_attach_volume(self):
        flavors = self.nova_client.flavors.list()
        images = self.nova_client.images.list()
        volume = self.create_volume(1, "fake_name")
        oskey = self.nova_client.keypairs.create("oskeypriv")
        instance = self.create_nova("osinstance",
                                    images[0],
                                    flavors[0],
                                    key_name=oskey.name)
        self.create_server_volume(instance.id, volume.id, r"/dev/vdc")
        volume_res = self.cinder_client.volumes.get(volume.id)
        ins_res = self.smaug_client.protectables.get_instance(
            'OS::Nova::Server', volume_res.attachments[0]["server_id"])
        self.assertTrue(ins_res.dependent_resources)
        self.assertEqual('OS::Cinder::Volume',
                         ins_res.dependent_resources[0]["type"])
        self.delete_server_volume(instance.id, volume.id)
        self.nova_client.keypairs.delete(oskey.name)
        self.delete_volume(volume.id)
        self.delete_nova(instance.id)
