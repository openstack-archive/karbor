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


class CheckpointsTest(smaug_base.SmaugBaseTest):
    """Test Checkpoints operation """

    def test_checkpoint_create(self):
        providers = self.provider_list()
        self.assertTrue(len(providers))
        provider_id = providers[0].id

        volume = self.create_volume(1, "Volume1")
        plan = self.create_plan(smaug_base.PLAN_NORMAL_NAME,
                                provider_id,
                                volume,
                                smaug_base.PLAN_NORMAL_PARAM)
        plan_id = plan.get("id")

        backups = self.cinder_client.backups.list()
        before_num = len(backups)

        checkpoint = self.create_checkpoint(provider_id, plan_id, volume.id)

        backups_ = self.cinder_client.backups.list()
        after_num = len(backups_)
        self.assertEqual(1, after_num - before_num)

        # cleanup
        self.delete_checkpoint(provider_id, checkpoint["id"])
        self.smaug_client.plans.delete(plan_id)
        self.delete_volume(volume.id)

    def test_checkpoint_delete(self):
        providers = self.provider_list()
        self.assertTrue(len(providers))
        provider_id = providers[0].id

        volume = self.create_volume(1, "Volume1")
        plan = self.create_plan(smaug_base.PLAN_NORMAL_NAME,
                                provider_id,
                                volume,
                                smaug_base.PLAN_NORMAL_PARAM)
        plan_id = plan.get("id")

        backups = self.smaug_client.checkpoints.list(provider_id)
        before_num = len(backups)

        checkpoint = self.create_checkpoint(provider_id, plan_id, volume.id)
        # checkpoint_ = self.smaug_client.checkpoints.get(provider_id,
        #                                                 checkpoint['id'])
        # self.assertEqual("committed", checkpoint_.status)
        self.delete_checkpoint(provider_id, checkpoint["id"])
        backups_ = self.smaug_client.checkpoints.list(provider_id)
        after_num = len(backups_)
        self.assertEqual(before_num, after_num)

        # cleanup
        self.smaug_client.plans.delete(plan_id)
        self.delete_volume(volume.id)
