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

    def create_plan(self, provider_id, volume_id):
        plan1 = self.smaug_client.plans.create(
            "My plan app1",
            provider_id,
            [{"id": volume_id,
              "type": "OS::Cinder::Volume",
              "name": "fake_name"}],
            {"OS::Nova::Server": {"consistency": "os"}})
        plan2 = self.smaug_client.plans.create(
            "My plan app2",
            provider_id,
            [{"id": volume_id,
              "type": "OS::Cinder::Volume",
              "name": "fake_name"}],
            {"OS::Nova::Server": {"consistency": "os"}})
        return plan1, plan2

    def test_plans_create(self):
        # retrieve providers
        providers = self.provider_list()
        self.assertTrue(len(providers))
        # create volume
        volume = self.create_volume(1)
        # get num of plans before creating
        plans = self.smaug_client.plans.list()
        before_num = len(plans)
        # create plan
        plan1, plan2 = self.create_plan(providers[0].id, volume.id)
        # get num of plans after creating
        plans_ = self.smaug_client.plans.list()
        after_num = len(plans_)
        self.assertEqual(2, after_num - before_num)
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)

    def test_plans_list(self):
        self.cleanup_plans()
        # retrieve providers
        providers = self.provider_list()
        self.assertTrue(len(providers))
        # create plan
        volume = self.create_volume(1)
        plan1, plan2 = self.create_plan(providers[0].id, volume.id)
        # list plans after creating
        plan_item = self.smaug_client.plans.list()
        self.assertEqual(2, len(plan_item))
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)

    def test_plans_get(self):
        # retrieve providers
        providers = self.provider_list()
        self.assertTrue(len(providers))
        # create plan
        volume = self.create_volume(1)
        plan1, plan2 = self.create_plan(providers[0].id, volume.id)
        # get plan
        plan_item1 = self.smaug_client.plans.get(plan1.get("id"))
        self.assertEqual("My plan app1", plan_item1.name)
        plan_item2 = self.smaug_client.plans.get(plan2.get("id"))
        self.assertEqual("My plan app2", plan_item2.name)
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)

    def test_plans_update(self):
        # retrieve providers
        providers = self.provider_list()
        self.assertTrue(len(providers))
        # create plan
        volume = self.create_volume(1, "Volume1")
        plan1, plan2 = self.create_plan(providers[0].id, volume.id)
        # get old plan
        plan_old = self.smaug_client.plans.get(plan1.get("id"))
        self.assertEqual("My plan app1", plan_old.name)
        self.assertEqual("suspended", plan_old.status)
        self.assertEqual([{"id": volume.id,
                           "type": "OS::Cinder::Volume",
                           "name": "fake_name"}],
                         plan_old.resources)
        # update name
        data = {"name": "fake_plan"}
        plan_item = self.smaug_client.plans.update(plan1.get("id"), data)
        self.assertEqual("fake_plan", plan_item.name)
        # update resources
        data = {"resources": [{"id": volume.id,
                               "type": "OS::Cinder::Volume",
                               "name": volume.name}]}
        plan_item = self.smaug_client.plans.update(plan1.get("id"), data)
        self.assertEqual([{"id": volume.id,
                           "type": "OS::Cinder::Volume",
                           "name": volume.name}],
                         plan_item.resources)
        # update status
        data = {"status": "started"}
        plan_item = self.smaug_client.plans.update(plan1.get("id"), data)
        self.assertEqual("started", plan_item.status)
        # cleanup
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
        self.delete_volume(volume.id)
