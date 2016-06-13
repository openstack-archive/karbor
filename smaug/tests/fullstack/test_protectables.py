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
import time


class ProtectablesTest(smaug_base.SmaugBaseTest):
    """Test Protectables operation"""

    def create_volume(self, size):
        volume = self.cinder_client.volumes.create(size)
        time.sleep(5)
        return volume

    def delete_volume(self, volume_id):
        self.cinder_client.volumes.delete(volume_id)
        time.sleep(15)

    def test_protectables_list(self):
        res = self.smaug_client.protectables.list()
        self.assertTrue(len(res))

    def test_protectables_get_with_project(self):
        protectable_type = 'OS::Keystone::Project'
        res = self.smaug_client.protectables.get(protectable_type)
        dependent_types = ['OS::Cinder::Volume', 'OS::Nova::Server']
        self.assertEqual(dependent_types, res.dependent_types)

    def test_protectables_list_instances(self):
        res_list = self.smaug_client.protectables.list_instances(
            'OS::Cinder::Volume')
        before_num = len(res_list)
        volume_1 = self.create_volume(1)
        volume_2 = self.create_volume(1)
        res = self.smaug_client.protectables.list_instances(
            'OS::Cinder::Volume')
        after_num = len(res)
        self.assertEqual(2, after_num - before_num)
        self.delete_volume(volume_1.id)
        self.delete_volume(volume_2.id)
