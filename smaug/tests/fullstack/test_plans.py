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


class PlansTest(smaug_base.SmaugBaseTest):
    """Test Plans operation"""

    def test_plans_create(self):
        providers = self.provider_list()
        self.assertTrue(len(providers))
        provider_id = providers[0].id

        plans = self.smaug_client.plans.list()
        before_num = len(plans)

        volume = self.create_volume(1)
        plan1 = self.create_plan(smaug_base.PLAN_NORMAL_NAME,
                                 provider_id,
                                 volume,
                                 smaug_base.PLAN_NORMAL_PARAM)
        plan2 = self.create_plan(smaug_base.PLAN_NORMAL_NAME,
                                 provider_id,
                                 volume,
                                 smaug_base.PLAN_NORMAL_PARAM)

        plans_ = self.smaug_client.plans.list()
        after_num = len(plans_)
        self.assertEqual(2, after_num - before_num)

        # cleanup
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)

    def test_plans_list(self):
        self.cleanup_plans()

        providers = self.provider_list()
        self.assertTrue(len(providers))
        provider_id = providers[0].id

        volume = self.create_volume(1)
        plan1 = self.create_plan(smaug_base.PLAN_NORMAL_NAME,
                                 provider_id,
                                 volume,
                                 smaug_base.PLAN_NORMAL_PARAM)
        plan2 = self.create_plan(smaug_base.PLAN_NORMAL_NAME,
                                 provider_id,
                                 volume,
                                 smaug_base.PLAN_NORMAL_PARAM)

        plan_item = self.smaug_client.plans.list()
        self.assertEqual(2, len(plan_item))

        # cleanup
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)

    def test_plans_get(self):
        providers = self.provider_list()
        self.assertTrue(len(providers))
        provider_id = providers[0].id

        volume = self.create_volume(1)
        plan1 = self.create_plan("My plan app1",
                                 provider_id,
                                 volume,
                                 smaug_base.PLAN_NORMAL_PARAM)
        plan2 = self.create_plan("My plan app2",
                                 provider_id,
                                 volume,
                                 smaug_base.PLAN_NORMAL_PARAM)

        plan_item1 = self.smaug_client.plans.get(plan1.get("id"))
        self.assertEqual("My plan app1", plan_item1.name)
        plan_item2 = self.smaug_client.plans.get(plan2.get("id"))
        self.assertEqual("My plan app2", plan_item2.name)

        # cleanup
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)

    def test_plans_update(self):
        providers = self.provider_list()
        self.assertTrue(len(providers))
        provider_id = providers[0].id

        volume1 = self.create_volume(1, "Volume1")
        volume2 = self.create_volume(1, "Volume2")
        plan1 = self.create_plan("My plan app1",
                                 provider_id,
                                 volume1,
                                 smaug_base.PLAN_NORMAL_PARAM)
        plan2 = self.create_plan("My plan app2",
                                 provider_id,
                                 volume2,
                                 smaug_base.PLAN_NORMAL_PARAM)

        plan_old = self.smaug_client.plans.get(plan1.get("id"))
        self.assertEqual("My plan app1", plan_old.name)
        self.assertEqual("suspended", plan_old.status)
        self.assertEqual([{"id": volume1.id,
                           "type": "OS::Cinder::Volume",
                           "name": volume1.name}],
                         plan_old.resources)

        # update name
        data = {"name": "fake_plan"}
        plan_item = self.smaug_client.plans.update(plan1.get("id"), data)
        self.assertEqual("fake_plan", plan_item.name)

        # update resources
        data = {"resources": [{"id": volume2.id,
                               "type": "OS::Cinder::Volume",
                               "name": volume2.name}]}
        plan_item = self.smaug_client.plans.update(plan1.get("id"), data)
        self.assertEqual([{"id": volume2.id,
                           "type": "OS::Cinder::Volume",
                           "name": volume2.name}],
                         plan_item.resources)

        # update status
        data = {"status": "started"}
        plan_item = self.smaug_client.plans.update(plan1.get("id"), data)
        self.assertEqual("started", plan_item.status)

        # cleanup
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume1.id)
        self.delete_volume(volume2.id)
