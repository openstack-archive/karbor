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

from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects


class RestoresTest(karbor_base.KarborBaseTest):
    """Test Restores operation """
    parameters = {}
    restore_auth = {
        "type": "password",
        "username": "admin",
        "password": "password",
    }

    def setUp(self):
        super(RestoresTest, self).setUp()

    def _store_volume(self, volumes_pre, volumes_post):
        volumes = list(set(volumes_post).difference(set(volumes_pre)))
        for volume in volumes:
            volume_ = objects.Volume()
            volume_.id = volume.id
            self.store(volume_)

    @staticmethod
    def get_restore_target(endpoint):
        regex = re.compile(
            r'http[s]?://\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', re.IGNORECASE
        )
        url = re.search(regex, endpoint).group()
        restore_target = url + r":35357/v3"
        return restore_target

    def test_restore_create(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restores = self.karbor_client.restores.list()
        before_num = len(restores)
        volumes_pre = self.cinder_client.volumes.list()

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id_noop, checkpoint.id,
                       restore_target, self.parameters, self.restore_auth)

        restores = self.karbor_client.restores.list()
        after_num = len(restores)
        self.assertEqual(1, after_num - before_num)

        volumes_post = self.cinder_client.volumes.list()
        self._store_volume(volumes_pre, volumes_post)

    def test_restore_create_without_target_and_auth(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restores = self.karbor_client.restores.list()
        before_num = len(restores)
        volumes_pre = self.cinder_client.volumes.list()

        restore = self.store(objects.Restore())
        restore.create(self.provider_id_noop, checkpoint.id,
                       None, self.parameters, None)

        restores = self.karbor_client.restores.list()
        after_num = len(restores)
        self.assertEqual(1, after_num - before_num)

        volumes_post = self.cinder_client.volumes.list()
        self._store_volume(volumes_pre, volumes_post)

    def test_restore_get(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        volumes_pre = self.cinder_client.volumes.list()

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id_noop, checkpoint.id,
                       restore_target, self.parameters, self.restore_auth)

        restore_item = self.karbor_client.restores.get(restore.id)
        self.assertEqual(restore.id, restore_item.id)

        volumes_post = self.cinder_client.volumes.list()
        self._store_volume(volumes_pre, volumes_post)

    def test_restore_list(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restores = self.karbor_client.restores.list()
        before_num = len(restores)
        volumes_pre = self.cinder_client.volumes.list()

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore1 = self.store(objects.Restore())
        restore1.create(self.provider_id_noop, checkpoint.id,
                        restore_target, self.parameters, self.restore_auth)
        restore2 = self.store(objects.Restore())
        restore2.create(self.provider_id_noop, checkpoint.id,
                        restore_target, self.parameters, self.restore_auth)

        restores = self.karbor_client.restores.list()
        after_num = len(restores)
        self.assertEqual(2, after_num - before_num)

        volumes_post = self.cinder_client.volumes.list()
        self._store_volume(volumes_pre, volumes_post)

    def test_restore_resources(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_os, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_os, plan.id)
        volumes_pre = self.cinder_client.volumes.list()
        restore = self.store(objects.Restore())
        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore_id = restore.create(
            self.provider_id_os,
            checkpoint.id,
            restore_target,
            self.parameters,
            self.restore_auth,
        )
        restore_obj = self.karbor_client.restores.get(restore_id)
        self.assertEqual(len(restore_obj.resources_status), 1)
        volumes_post = self.cinder_client.volumes.list()
        self._store_volume(volumes_pre, volumes_post)
