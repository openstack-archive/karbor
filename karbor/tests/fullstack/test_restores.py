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

from oslo_utils import importutils

from karbor.common import constants
from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects

DELETABLE_STATUS = {
    "volume_deletable_status": ["available", "error"],
    "server_deletable_status": ["available", "running"]
}


class RestoresTest(karbor_base.KarborBaseTest):
    """Test Restores operation """
    parameters = {}
    restore_auth = {
        "type": "password",
        "username": "admin",
        "password": "password",
    }

    def _store(self, resources_status):
        if not isinstance(resources_status, dict):
            return

        for resource, status in resources_status.items():
            resource_type, resource_id = resource.split("#")
            if resource_type is None:
                continue

            types = resource_type.split("::")
            if len(types) < 3:
                continue

            try:
                obj_class = importutils.import_class(
                    "karbor.tests.fullstack.karbor_objects.%s" % types[2])
            except Exception:
                continue

            deletable_str = "%s_deletable_status" % types[2].lower()
            deletable_list = eval(deletable_str, DELETABLE_STATUS)
            if callable(obj_class) and status in deletable_list:
                obj = obj_class()
                obj.id = resource_id
                obj.close()

    @staticmethod
    def get_restore_target(endpoint):
        regex = re.compile(
            r'http[s]?://\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', re.IGNORECASE
        )
        url = re.search(regex, endpoint).group()
        restore_target = url + r"/identity/v3"
        return restore_target

    def test_restore_create(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id_noop, checkpoint.id,
                       restore_target, self.parameters, self.restore_auth)

        item = self.karbor_client.restores.get(restore.id)
        self.assertEqual(constants.RESTORE_STATUS_SUCCESS,
                         item.status)
        self._store(item.resources_status)

    def test_restore_create_without_target_and_auth(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restore = self.store(objects.Restore())
        restore.create(self.provider_id_noop, checkpoint.id,
                       None, self.parameters, None)

        item = self.karbor_client.restores.get(restore.id)
        self.assertEqual(constants.RESTORE_STATUS_SUCCESS,
                         item.status)
        self._store(item.resources_status)

    def test_restore_get(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id_noop, checkpoint.id,
                       restore_target, self.parameters, self.restore_auth)

        item = self.karbor_client.restores.get(restore.id)
        self.assertEqual(restore.id, item.id)
        self.assertEqual(constants.RESTORE_STATUS_SUCCESS,
                         item.status)
        self._store(item.resources_status)

    def test_restore_list(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_noop, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_noop, plan.id)

        restores = self.karbor_client.restores.list()
        before_num = len(restores)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore1 = self.store(objects.Restore())
        restore1.create(self.provider_id_noop, checkpoint.id,
                        restore_target, self.parameters, self.restore_auth)
        restore2 = self.store(objects.Restore())
        restore2.create(self.provider_id_noop, checkpoint.id,
                        restore_target, self.parameters, self.restore_auth)

        restores = self.karbor_client.restores.list()
        after_num = len(restores)
        self.assertLessEqual(2, after_num - before_num)

        item1 = self.karbor_client.restores.get(restore1.id)
        self._store(item1.resources_status)
        item2 = self.karbor_client.restores.get(restore2.id)
        self._store(item2.resources_status)

    def test_restore_resources(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_os, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_os, plan.id)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id_os, checkpoint.id,
                       restore_target, self.parameters, self.restore_auth)

        item = self.karbor_client.restores.get(restore.id)
        self.assertEqual(constants.RESTORE_STATUS_SUCCESS,
                         item.status)
        self.assertEqual(1, len(item.resources_status))
        self._store(item.resources_status)

    def test_restore_resources_with_fs_bank(self):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id_fs_bank, [volume, ])
        checkpoint = self.store(objects.Checkpoint())
        checkpoint.create(self.provider_id_fs_bank, plan.id)

        restore_target = self.get_restore_target(self.keystone_endpoint)
        restore = self.store(objects.Restore())
        restore.create(self.provider_id_fs_bank, checkpoint.id,
                       restore_target, self.parameters, self.restore_auth)

        item = self.karbor_client.restores.get(restore.id)
        self.assertEqual(constants.RESTORE_STATUS_SUCCESS,
                         item.status)
        self.assertEqual(1, len(item.resources_status))
        self._store(item.resources_status)
