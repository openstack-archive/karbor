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


class PlansTest(karbor_base.KarborBaseTest):
    """Test Plans operation"""
    def setUp(self):
        super(PlansTest, self).setUp()
        self.provider_id = self.provider_id_noop

    def test_plans_list(self):
        # create plan
        volume = self.store(objects.Volume())
        volume.create(1)
        plan1 = self.store(objects.Plan())
        plan1.create(self.provider_id, [volume, ])
        plan2 = self.store(objects.Plan())
        plan2.create(self.provider_id, [volume, ])

        # list plans after creating
        items = self.karbor_client.plans.list()
        ids = [item.id for item in items]
        self.assertTrue(plan1.id in ids)
        self.assertTrue(plan2.id in ids)

    def test_plans_get(self):
        plan_name = "Fullstack Test Get"
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ], name=plan_name)

        plan_item = self.karbor_client.plans.get(plan.id)
        self.assertEqual(plan_name, plan_item.name)

    def test_plans_update(self):
        plan_initial_name = "Fullstack Plan Pre-Update"
        plan_updated_name = "Fullstack Plan Post-Update"
        volume1_name = "Fullstack Plan Update Volume1"
        volume2_name = "Fullstack Plan Update Volume2"
        volume1 = self.store(objects.Volume())
        volume1.create(1, name=volume1_name)
        volume2 = self.store(objects.Volume())
        volume2.create(1, name=volume2_name)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume1, ], name=plan_initial_name)

        # sanity
        plan_item = self.karbor_client.plans.get(plan.id)
        self.assertEqual(plan_initial_name, plan_item.name)
        self.assertEqual("suspended", plan_item.status)
        self.assertEqual([{"id": volume1.id,
                           "type": constants.VOLUME_RESOURCE_TYPE,
                           "name": volume1_name,
                           "extra_info":
                               {"availability_zone": "az1"}}],
                         plan_item.resources)

        # update name
        data = {"name": plan_updated_name}
        plan_item = self.karbor_client.plans.update(plan.id, data)
        self.assertEqual(plan_updated_name, plan_item.name)

        # update resources
        data = {"resources": [volume2.to_dict(), ]}
        plan_item = self.karbor_client.plans.update(plan.id, data)
        self.assertEqual([{"id": volume2.id,
                           "type": constants.VOLUME_RESOURCE_TYPE,
                           "name": volume2_name,
                           "extra_info":
                               {"availability_zone": "az1"}}],
                         plan_item.resources)

        # update status
        data = {"status": "started"}
        plan_item = self.karbor_client.plans.update(plan.id, data)
        self.assertEqual("started", plan_item.status)
