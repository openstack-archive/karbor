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


class SmaugTest(smaug_base.SmaugBaseTest):
    """Test Smaug operation

    """
    def test_smaug(self):
        pass

    def test_plan_list(self):
        plan = self.smaug_client.plans.create(
            "My 3 tier application",
            "2220f8b1-975d-4621-a872-fa9afb43cb6c",
            [{"type": "OS::Cinder::Volume",
              "name": "fake_name",
             "id": "5fad94de-2926-486b-ae73-ff5d3477f80d"}],
            {"parameters": {"OS::Nova::Server": {"consistency": "os"}}})
        plan_id = plan.get("id")
        plan_item = self.smaug_client.plans.get(plan_id)
        plan_item_id = plan_item.id
        self.assertEqual(plan_id, plan_item_id)
