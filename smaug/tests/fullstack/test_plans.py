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
import utils


class PlansTest(smaug_base.SmaugBaseTest):
    """Test Plans operation

    """

    def create_plan(self):
        plan1 = self.smaug_client.plans.create(
            "My plan app1",
            "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
            [{"type": "OS::Cinder::Volume",
              "name": "fake_name",
              "id": "5fad94de-2926-486b-ae73-ff5d3477f80d"}],
            {"parameters": {"OS::Nova::Server": {"consistency": "os"}}})
        plan2 = self.smaug_client.plans.create(
            "My plan app2",
            "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
            [{"type": "OS::Cinder::Volume",
              "name": "fake_name",
              "id": "5fad94de-2926-486b-ae73-ff5d3477f80d"}],
            {"parameters": {"OS::Nova::Server": {"consistency": "os"}}})
        return plan1, plan2

    def test_plans_create(self):
        plan1, plan2 = self.create_plan()
        plan_item = utils.wait_until_is_and_return(
            lambda: self.smaug_client.plans.get(plan1.get("id")),
            exception=Exception('No plan data in db')
        )
        self.assertEqual("My plan app1", plan_item.name)
        self.assertEqual(plan1.get("id"), plan_item.id)
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))

    def test_plans_list(self):
        plan1, plan2 = self.create_plan()
        plan_item = utils.wait_until_is_and_return(
            lambda: self.smaug_client.plans.list(),
            exception=Exception('No plan data in db')
        )
        self.assertEqual(2, len(plan_item))
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))

    def test_plans_get(self):
        plan1, plan2 = self.create_plan()
        plan_item = utils.wait_until_is_and_return(
            lambda: self.smaug_client.plans.get(plan1.get("id")),
            exception=Exception('No plan data in db')
        )
        self.assertEqual("My plan app1", plan_item.name)
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))

    def test_plans_update(self):
        plan1, plan2 = self.create_plan()
        plan = self.smaug_client.plans.get(plan1.get("id"))
        self.assertEqual("My plan app1", plan.name)
        data = {"name": "fake_plan"}
        plan_item = self.smaug_client.plans.update(plan2.get("id"), data)
        self.assertEqual("fake_plan", plan_item.name)
        self.smaug_client.plans.delete(plan1.get("id"))
        self.smaug_client.plans.delete(plan2.get("id"))
