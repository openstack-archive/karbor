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
        volume_parameter_key = "OS::Cinder::Volume#{id}".format(id=volume.id)
        backup_name = "volume-backup-{id}".format(id=volume.id)
        parameters = {
            "OS::Cinder::Volume": {
                "backup_mode": "full",
                "force": False
            },
            volume_parameter_key: {
                "backup_name": backup_name
            }
        }
        plan.create(self.provider_id_os, [volume, ],
                    parameters=parameters)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        search_opts = {"volume_id": volume.id}
        backups = self.cinder_client.backups.list(search_opts=search_opts)
        self.assertEqual(1, len(backups))

        search_opts = {"name": backup_name}
        backups = self.cinder_client.backups.list(search_opts=search_opts)
        self.assertEqual(1, len(backups))

    def test_checkpoint_delete(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])

        checkpoint = objects.Checkpoint()
        checkpoint.create(self.provider_id, plan.id, timeout=2400)
        checkpoint_item = self.karbor_client.checkpoints.get(self.provider_id,
                                                             checkpoint.id)
        self.assertEqual(constants.CHECKPOINT_STATUS_AVAILABLE,
                         checkpoint_item.status)

        checkpoint.close()
        items = self.karbor_client.checkpoints.list(self.provider_id)
        ids = [item.id for item in items]
        self.assertTrue(checkpoint.id not in ids)

    def test_checkpoint_list(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        items = self.karbor_client.checkpoints.list(self.provider_id)
        ids = [item.id for item in items]
        self.assertTrue(checkpoint.id in ids)

    def test_checkpoint_get(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        # sanity
        checkpoint_item = self.karbor_client.checkpoints.get(self.provider_id,
                                                             checkpoint.id)
        self.assertEqual(constants.CHECKPOINT_STATUS_AVAILABLE,
                         checkpoint_item.status)
        self.assertEqual(checkpoint.id, checkpoint_item.id)

    def test_server_attached_volume_only_protect_server(self):
        """Test checkpoint for server with attached volume

        Test checkpoint for server which has attached one volume,
        but only add server in protect source
        """
        volume = self.store(objects.Volume())
        volume.create(1)
        server = self.store(objects.Server())
        server.create()
        server.attach_volume(volume.id)

        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [server, ])

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        items = self.karbor_client.checkpoints.list(self.provider_id)
        ids = [item.id for item in items]
        self.assertTrue(checkpoint.id in ids)
        search_opts = {"volume_id": volume.id}
        backups = self.cinder_client.backups.list(search_opts=search_opts)
        self.assertEqual(1, len(backups))
        server.detach_volume(volume.id)

    def test_server_attached_volume_protect_both(self):
        """Test checkpoint for server with attached volume

        Test checkpoint for server which has attached one volume,
        and add server and volume both in protect source
        """
        volume = self.store(objects.Volume())
        volume.create(1)
        server = self.store(objects.Server())
        server.create()
        server.attach_volume(volume.id)

        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [server, volume])

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        items = self.karbor_client.checkpoints.list(self.provider_id)
        ids = [item.id for item in items]
        self.assertTrue(checkpoint.id in ids)
        search_opts = {"volume_id": volume.id}
        backups = self.cinder_client.backups.list(search_opts=search_opts)
        self.assertEqual(1, len(backups))
        server.detach_volume(volume.id)

    def test_server_boot_from_volume_with_attached_volume(self):
        """Test checkpoint for server with a bootable volume

        Test checkpoint for server which has booted form one bootable
        volume.
        """
        bootable_volume = self.store(objects.Volume())
        bootable_volume_id = bootable_volume.create(1, create_from_image=True)
        volume = self.store(objects.Volume())
        volume.create(1)
        server = self.store(objects.Server())
        server.create(volume=bootable_volume_id)
        server.attach_volume(volume.id)

        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [server, ])

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        items = self.karbor_client.checkpoints.list(self.provider_id)
        ids = [item.id for item in items]
        self.assertTrue(checkpoint.id in ids)
        search_opts = {"volume_id": volume.id}
        backups = self.cinder_client.backups.list(search_opts=search_opts)
        self.assertEqual(1, len(backups))
        search_opts = {"volume_id": bootable_volume_id}
        bootable_backups = self.cinder_client.backups.list(
            search_opts=search_opts)
        self.assertEqual(1, len(bootable_backups))
        server.detach_volume(volume.id)

    def test_checkpoint_share_projection(self):
        share = self.store(objects.Share())
        share.create("NFS", 1)
        plan = self.store(objects.Plan())

        share_parameter_key = "OS::Manila::Share#{id}".format(
            id=share.id)
        snapshot_name = "share-snapshot-{id}".format(id=share.id)
        parameters = {
            "OS::Manila::Share": {
                "force": False
            },
            share_parameter_key: {
                "snapshot_name": snapshot_name
            }
        }
        plan.create(self.provider_id_os, [share, ],
                    parameters=parameters)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id, plan.id, timeout=2400)

        search_opts = {"share_id": share.id}
        snapshots = self.manila_client.share_snapshots.list(
            search_opts=search_opts)
        self.assertEqual(1, len(snapshots))

        search_opts = {"name": snapshot_name}
        backups = self.manila_client.share_snapshots.list(
            search_opts=search_opts)
        self.assertEqual(1, len(backups))

    def test_checkpoint_volume_snapshot(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        volume_parameter_key = "OS::Cinder::Volume#{id}".format(id=volume.id)
        snapshot_name = "volume-snapshot-{id}".format(id=volume.id)
        parameters = {
            "OS::Cinder::Volume": {
                "force": False
            },
            volume_parameter_key: {
                "snapshot_name": snapshot_name
            }
        }
        plan.create(self.provider_id_os_volume_snapshot, [volume, ],
                    parameters=parameters)

        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_os_volume_snapshot, plan.id,
                          timeout=2400)

        search_opts = {"volume_id": volume.id}
        snapshots = self.cinder_client.volume_snapshots.list(
            search_opts=search_opts)
        self.assertEqual(1, len(snapshots))

        search_opts = {"name": snapshot_name}
        snapshots = self.cinder_client.volume_snapshots.list(
            search_opts=search_opts)
        self.assertEqual(1, len(snapshots))
