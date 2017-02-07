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

from karbor.common import constants
from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects


class CheckpointsTest(karbor_base.KarborBaseTest):
    """Test Checkpoints operation """
    def setUp(self):
        super(CheckpointsTest, self).setUp()
        self.provider_id = self.provider_id_os

    def test_checkpoint_create(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_os, [volume, ])

        backups = self.cinder_client.backups.list()
        before_num = len(backups)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id)

        backups = self.cinder_client.backups.list()
        after_num = len(backups)
        self.assertEqual(1, after_num - before_num)

    def test_checkpoint_delete(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        before_num = len(checkpoints)

        checkpoint = objects.Checkpoint()
        checkpoint.create(self.provider_id, plan.id)

        # sanity
        checkpoint_item = self.karbor_client.checkpoints.get(self.provider_id,
                                                             checkpoint.id)
        self.assertEqual(constants.CHECKPOINT_STATUS_AVAILABLE,
                         checkpoint_item.status)

        checkpoint.close()
        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        after_num = len(checkpoints)
        self.assertEqual(before_num, after_num)

    def test_checkpoint_list(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        before_num = len(checkpoints)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id)

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        after_num = len(checkpoints)
        self.assertEqual(1, after_num - before_num)

    def test_checkpoint_get(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id)

        # sanity
        checkpoint_item = self.karbor_client.checkpoints.get(self.provider_id,
                                                             checkpoint.id)
        self.assertEqual(constants.CHECKPOINT_STATUS_AVAILABLE,
                         checkpoint_item.status)
        self.assertEqual(checkpoint.id, checkpoint_item.id)

    def test_checkpoint_for_server_attached_volume(self):
        """Test checkpoint for server which has attached some volumes"""
        volume = self.store(objects.Volume())
        volume.create(1)
        server = self.store(objects.Server())
        server.create()
        server.attach_volume(volume.id)

        plan0 = self.store(objects.Plan())
        plan0.create(self.provider_id, [server, ])

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        before_checkpoints_num = len(checkpoints)
        backups = self.cinder_client.backups.list()
        before_backups_num = len(backups)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan0.id, timeout=900)

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        after_checkpoints_num = len(checkpoints)
        self.assertEqual(1, after_checkpoints_num - before_checkpoints_num)

        backups = self.cinder_client.backups.list()
        after_backups_num = len(backups)
        self.assertEqual(1, after_backups_num - before_backups_num)

        plan1 = self.store(objects.Plan())
        plan1.create(self.provider_id, [server, volume])

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        before_checkpoints_num = len(checkpoints)
        backups = self.cinder_client.backups.list()
        before_backups_num = len(backups)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan1.id, timeout=720)

        checkpoints = self.karbor_client.checkpoints.list(self.provider_id)
        after_checkpoints_num = len(checkpoints)
        self.assertEqual(1, after_checkpoints_num - before_checkpoints_num)

        backups = self.cinder_client.backups.list()
        after_backups_num = len(backups)
        self.assertEqual(1, after_backups_num - before_backups_num)

        server.detach_volume(volume.id)
