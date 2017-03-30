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

from karbor.resource import Resource
from karbor.services.protection import bank_plugin
from karbor.services.protection import checkpoint
from karbor.services.protection import graph

from karbor.tests import base
from karbor.tests.unit.protection.fakes import fake_protection_plan
from karbor.tests.unit.protection.test_bank import _InMemoryBankPlugin
from karbor.tests.unit.protection.test_bank import _InMemoryLeasePlugin

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
    def test_create_in_section(self):
        bank = bank_plugin.Bank(_InMemoryBankPlugin())
        bank_lease = _InMemoryLeasePlugin()
        checkpoints_section = bank_plugin.BankSection(bank, "/checkpoints")
        indices_section = bank_plugin.BankSection(bank, "/indices")
        owner_id = bank.get_owner_id()
        plan = fake_protection_plan()
        cp = checkpoint.Checkpoint.create_in_section(
            checkpoints_section=checkpoints_section,
            indices_section=indices_section,
            bank_lease=bank_lease,
            owner_id=owner_id,
            plan=plan)
        checkpoint_data = cp._md_cache
        self.assertEqual(
            checkpoint_data,
            bank._plugin.get_object(
                "/checkpoints/%s/%s" % (checkpoint_data['id'],
                                        checkpoint._INDEX_FILE_NAME)
            )
        )
        self.assertEqual(owner_id, cp.owner_id)
        self.assertEqual("protecting", cp.status)

    def test_resource_graph(self):
        bank = bank_plugin.Bank(_InMemoryBankPlugin())
        bank_lease = _InMemoryLeasePlugin()
        checkpoints_section = bank_plugin.BankSection(bank, "/checkpoints")
        indices_section = bank_plugin.BankSection(bank, "/indices")
        owner_id = bank.get_owner_id()
        plan = fake_protection_plan()
        cp = checkpoint.Checkpoint.create_in_section(
            checkpoints_section=checkpoints_section,
            indices_section=indices_section,
            bank_lease=bank_lease,
            owner_id=owner_id,
            plan=plan)

        resource_graph = graph.build_graph([A, B, C, D],
                                           resource_map.__getitem__)
        cp.resource_graph = resource_graph
        cp.commit()
        checkpoint_data = cp._md_cache
        self.assertEqual(
            checkpoint_data,
            bank._plugin.get_object(
                "/checkpoints/%s/%s" % (checkpoint_data["id"],
                                        checkpoint._INDEX_FILE_NAME)
            )
        )
        self.assertEqual(len(resource_graph), len(cp.resource_graph))
        for start_node in resource_graph:
            self.assertIn(start_node, cp.resource_graph)
