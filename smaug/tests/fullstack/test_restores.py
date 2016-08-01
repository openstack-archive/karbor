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

import re
from smaug.tests.fullstack import smaug_base
from smaug.tests.fullstack import smaug_objects as objects


class RestoresTest(smaug_base.SmaugBaseTest):
    """Test Restores operation """
    parameters = {"username": "admin", "password": "secretadmin"}

    def setUp(self):
        super(RestoresTest, self).setUp()
        providers = self.provider_list()
        self.assertTrue(len(providers))
        self.provider_id = providers[0].id

    def tearDown(self):
        self.cleanup_volumes()
        super(RestoresTest, self).tearDown()

    def cleanup_volumes(self):
        volumes = self.cinder_client.volumes.list()
        for volume in volumes:
            if "available" == volume.status:
                self.cinder_client.volumes.delete(volume.id)

    @staticmethod
    def get_restore_target(endpoint):
        regex = re.compile(
            r'http[s]?://\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', re.IGNORECASE
        )
        url = re.search(regex, endpoint).group()
        restore_target = url + r":35357/v2.0"
        return restore_target

    def test_restore_create(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id)

        restores = self.smaug_client.restores.list()
        before_num = len(restores)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id, checkpoint.id,
                       restore_target, self.parameters)

        restores = self.smaug_client.restores.list()
        after_num = len(restores)
        self.assertEqual(1, after_num - before_num)

    def test_restore_get(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id, checkpoint.id,
                       restore_target, self.parameters)

        restore_item = self.smaug_client.restores.get(restore.id)
        self.assertEqual(restore.id, restore_item.id)

    def test_restore_list(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id)

        restores = self.smaug_client.restores.list()
        before_num = len(restores)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore1 = self.store(objects.Restore())
        restore1.create(self.provider_id, checkpoint.id,
                        restore_target, self.parameters)
        restore2 = self.store(objects.Restore())
        restore2.create(self.provider_id, checkpoint.id,
                        restore_target, self.parameters)

        restores = self.smaug_client.restores.list()
        after_num = len(restores)
        self.assertEqual(2, after_num - before_num)
