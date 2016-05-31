# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from smaug.resource import Resource
from smaug.services.protection import bank_plugin
from smaug.services.protection.checkpoint import Checkpoint
from smaug.services.protection import graph

from smaug.tests import base
from smaug.tests.unit.protection.fakes import fake_protection_plan
from smaug.tests.unit.protection.test_bank import _InMemoryBankPlugin
from smaug.tests.unit.protection.test_bank import _InMemoryLeasePlugin

A = Resource(id="A", type="fake", name="fake")
B = Resource(id="B", type="fake", name="fake")
C = Resource(id="C", type="fake", name="fake")
D = Resource(id="D", type="fake", name="fake")
E = Resource(id="E", type="fake", name="fake")

resource_map = {
    A: [C],
    B: [C],
    C: [D, E],
    D: [],
    E: [],
}


class CheckpointTest(base.TestCase):
    def setUp(self):
        super(CheckpointTest, self).setUp()

    def test_create_in_section(self):
        bank = bank_plugin.Bank(_InMemoryBankPlugin())
        bank_lease = _InMemoryLeasePlugin()
        bank_section = bank_plugin.BankSection(bank, "/checkpoints")
        owner_id = bank.get_owner_id()
        plan = fake_protection_plan()
        checkpoint = Checkpoint.create_in_section(bank_section=bank_section,
                                                  bank_lease=bank_lease,
                                                  owner_id=owner_id,
                                                  plan=plan)
        checkpoint_data = {
            "version": Checkpoint.VERSION,
            "id": checkpoint.id,
            "status": "protecting",
            "owner_id": owner_id,
            "protection_plan": {
                "id": plan.get("id"),
                "name": plan.get("name"),
                "resources": plan.get("resources")
            }
        }
        self.assertEqual(
            checkpoint_data,
            bank._plugin.get_object(
                "/checkpoints%s" % checkpoint._index_file_path
            )
        )
        self.assertEqual(owner_id, checkpoint.owner_id)
        self.assertEqual("protecting", checkpoint.status)

    def test_resource_graph(self):
        bank = bank_plugin.Bank(_InMemoryBankPlugin())
        bank_lease = _InMemoryLeasePlugin()
        bank_section = bank_plugin.BankSection(bank, "/checkpoints")
        owner_id = bank.get_owner_id()
        plan = fake_protection_plan()
        checkpoint = Checkpoint.create_in_section(bank_section=bank_section,
                                                  bank_lease=bank_lease,
                                                  owner_id=owner_id,
                                                  plan=plan)

        resource_graph = graph.build_graph([A, B, C, D],
                                           resource_map.__getitem__)
        checkpoint.resource_graph = resource_graph
        checkpoint.commit()
        checkpoint_data = {
            "version": Checkpoint.VERSION,
            "id": checkpoint.id,
            "status": "protecting",
            "owner_id": owner_id,
            "protection_plan": {
                "id": plan.get("id"),
                "name": plan.get("name"),
                "resources": plan.get("resources")
            },
            "resource_graph": graph.serialize_resource_graph(
                resource_graph)
        }
        self.assertEqual(
            checkpoint_data,
            bank._plugin.get_object(
                "/checkpoints%s" % checkpoint._index_file_path
            )
        )
        self.assertEqual(len(resource_graph), len(checkpoint.resource_graph))
        for start_node in resource_graph:
            self.assertEqual(True, start_node in checkpoint.resource_graph)
