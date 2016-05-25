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

import mock

from smaug.services.protection.bank_plugin import Bank
from smaug.services.protection.checkpoint import CheckpointCollection
from smaug.tests import base
from smaug.tests.unit.protection.fakes import fake_protection_plan
from smaug.tests.unit.protection.test_bank import _InMemoryBankPlugin
from smaug.tests.unit.protection.test_bank import _InMemoryLeasePlugin


class CheckpointCollectionTest(base.TestCase):
    def _create_test_collection(self):
        return CheckpointCollection(Bank(_InMemoryBankPlugin()),
                                    _InMemoryLeasePlugin())

    def test_create_checkpoint(self):
        collection = self._create_test_collection()
        checkpoint = collection.create(fake_protection_plan())
        checkpoint.status = "finished"
        checkpoint.commit()
        self.assertEqual(
            checkpoint.status,
            collection.get(checkpoint_id=checkpoint.id).status,
        )

    def test_list_checkpoints(self):
        collection = self._create_test_collection()
        result = {
            collection.create(fake_protection_plan()).id for i in range(10)}
        self.assertEqual(set(collection.list_ids()), result)

    def test_delete_checkpoint(self):
        collection = self._create_test_collection()
        result = {
            collection.create(fake_protection_plan()).id for i in range(10)}
        checkpoint = collection.get(result.pop())
        checkpoint.purge()
        self.assertEqual(set(collection.list_ids()), result)

    def test_write_checkpoint_with_invalid_lease(self):
        collection = self._create_test_collection()
        checkpoint = collection.create(fake_protection_plan())
        collection._bank_lease.check_lease_validity = mock.MagicMock()
        collection._bank_lease.check_lease_validity.return_value = False
        checkpoint.status = "finished"
        self.assertNotEqual(
            checkpoint.status,
            collection.get(checkpoint_id=checkpoint.id).status,
        )
