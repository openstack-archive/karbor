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

from datetime import datetime
import mock

from oslo_utils import timeutils

from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.checkpoint import CheckpointCollection
from karbor.tests import base
from karbor.tests.unit.protection.fakes import fake_protection_plan
from karbor.tests.unit.protection.test_bank import _InMemoryBankPlugin
from karbor.tests.unit.protection.test_bank import _InMemoryLeasePlugin


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
        plan = fake_protection_plan()
        provider_id = plan['provider_id']
        project_id = plan['project_id']
        result = {collection.create(plan).id for i in range(10)}
        self.assertEqual(set(collection.list_ids(
            project_id=project_id, provider_id=provider_id)), result)

    def test_list_checkpoints_with_all_tenants(self):
        collection = self._create_test_collection()
        plan_1 = fake_protection_plan()
        plan_1["id"] = "fake_plan_id_1"
        plan_1["project_id"] = "fake_project_id_1"
        provider_id_1 = plan_1['provider_id']
        checkpoints_plan_1 = {collection.create(plan_1).id for i in range(10)}

        plan_2 = fake_protection_plan()
        plan_2["id"] = "fake_plan_id_2"
        plan_2["project_id"] = "fake_project_id_2"
        checkpoints_plan_2 = {collection.create(plan_2).id for i in range(10)}
        checkpoints_plan_1.update(checkpoints_plan_2)
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id_1", provider_id=provider_id_1,
            all_tenants=True)), checkpoints_plan_1)

    def test_list_checkpoints_by_plan_id(self):
        collection = self._create_test_collection()
        plan_1 = fake_protection_plan()
        plan_1["id"] = "fake_plan_id_1"
        plan_1['provider_id'] = "fake_provider_id_1"
        plan_1["project_id"] = "fake_project_id_1"
        provider_id_1 = plan_1['provider_id']
        checkpoints_plan_1 = {collection.create(plan_1).id for i in range(10)}

        plan_2 = fake_protection_plan()
        plan_2["id"] = "fake_plan_id_2"
        plan_2['provider_id'] = "fake_provider_id_2"
        plan_2["project_id"] = "fake_project_id_2"
        provider_id_2 = plan_1['provider_id']
        checkpoints_plan_2 = {collection.create(plan_2).id for i in range(10)}
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id_1", provider_id=provider_id_1,
            plan_id="fake_plan_id_1")), checkpoints_plan_1)
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id_2", provider_id=provider_id_2,
            plan_id="fake_plan_id_2")), checkpoints_plan_2)

    def test_list_checkpoints_by_plan_with_all_tenants(self):
        collection = self._create_test_collection()
        plan_1 = fake_protection_plan()
        plan_1["id"] = "fake_plan_id_1"
        plan_1["project_id"] = "fake_project_id_1"
        provider_id_1 = plan_1['provider_id']
        checkpoints_plan_1 = {collection.create(plan_1).id for i in range(10)}
        plan_1["project_id"] = "fake_project_id_2"
        checkpoints_plan_2 = {collection.create(plan_1).id for i in range(10)}
        checkpoints_plan_2.update(checkpoints_plan_1)
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id_1", provider_id=provider_id_1,
            plan_id='fake_plan_id_1',
            all_tenants=True)), checkpoints_plan_2)

    def test_list_checkpoints_by_plan_id_and_filter_by_start_date(self):
        collection = self._create_test_collection()
        date1 = datetime.strptime("2018-11-12", "%Y-%m-%d")
        date2 = datetime.strptime("2018-11-13", "%Y-%m-%d")
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date1
        plan = fake_protection_plan()
        plan["id"] = "fake_plan_id"
        plan['provider_id'] = "fake_provider_id"
        plan["project_id"] = "fake_project_id"
        provider_id = plan['provider_id']
        checkpoints_plan_date1 = {
            collection.create(plan).id for i in range(10)}
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date2
        checkpoints_plan_date2 = {
            collection.create(plan).id for i in range(10)}
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id", provider_id=provider_id,
            plan_id="fake_plan_id", start_date=date1, end_date=date1)),
            checkpoints_plan_date1)
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id", provider_id=provider_id,
            plan_id="fake_plan_id", start_date=date2)),
            checkpoints_plan_date2)

    def test_list_checkpoints_by_plan_with_marker(self):
        collection = self._create_test_collection()
        plan = fake_protection_plan()
        plan["id"] = "fake_plan_id"
        plan['provider_id'] = "fake_provider_id"
        plan["project_id"] = "fake_project_id"
        provider_id = plan['provider_id']
        checkpoints_plan = {collection.create(plan, {
            'checkpoint_id': i}).id for i in range(10)}
        checkpoints_sorted = sorted(checkpoints_plan)
        self.assertEqual(len(collection.list_ids(
            project_id="fake_project_id", provider_id=provider_id,
            plan_id="fake_plan_id", marker=checkpoints_sorted[0])) < 10, True)

    def test_list_checkpoints_by_date(self):
        collection = self._create_test_collection()
        date1 = datetime.strptime("2016-06-12", "%Y-%m-%d")
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date1
        plan = fake_protection_plan()
        provider_id = plan['provider_id']
        project_id = plan['project_id']
        checkpoints_date_1 = {collection.create(plan).id for i in range(10)}
        date2 = datetime.strptime("2016-06-13", "%Y-%m-%d")
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date2
        checkpoints_date_2 = {collection.create(plan).id for i in range(10)}
        self.assertEqual(set(collection.list_ids(
            project_id=project_id,
            provider_id=provider_id,
            start_date=date1,
            end_date=date1)),
            checkpoints_date_1)
        self.assertEqual(set(collection.list_ids(
            project_id=project_id,
            provider_id=provider_id,
            start_date=date2,
            end_date=date2)),
            checkpoints_date_2)

    def test_list_checkpoints_by_date_with_all_tenants(self):
        collection = self._create_test_collection()
        date1 = datetime.strptime("2018-11-15", "%Y-%m-%d")
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date1
        plan_1 = fake_protection_plan()
        plan_1["id"] = "fake_plan_id_1"
        plan_1["project_id"] = "fake_project_id_1"
        provider_id_1 = plan_1['provider_id']
        checkpoints_1 = {collection.create(plan_1).id for i in range(10)}

        date2 = datetime.strptime("2018-11-17", "%Y-%m-%d")
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date2
        plan_1["id"] = "fake_plan_id_2"
        plan_1["project_id"] = "fake_project_id_2"
        checkpoints_2 = {collection.create(plan_1).id for i in range(10)}
        checkpoints_2.update(checkpoints_1)
        self.assertEqual(set(collection.list_ids(
            project_id="fake_project_id_1", provider_id=provider_id_1,
            start_date=date1,
            all_tenants=True)), checkpoints_2)

    def test_list_checkpoints_by_date_with_marker(self):
        collection = self._create_test_collection()
        date = datetime.strptime("2018-11-12", "%Y-%m-%d")
        timeutils.utcnow = mock.MagicMock()
        timeutils.utcnow.return_value = date
        plan = fake_protection_plan()
        plan["id"] = "fake_plan_id"
        plan['provider_id'] = "fake_provider_id"
        plan["project_id"] = "fake_project_id"
        provider_id = plan['provider_id']
        checkpoints_plan = {collection.create(plan, {
            'checkpoint_id': i}).id for i in range(10)}
        checkpoints_sorted = sorted(checkpoints_plan)
        self.assertEqual(len(collection.list_ids(
            project_id="fake_project_id", provider_id=provider_id,
            start_date=date,
            marker=checkpoints_sorted[0])) < 10, True)

    def test_delete_checkpoint(self):
        collection = self._create_test_collection()
        plan = fake_protection_plan()
        provider_id = plan['provider_id']
        project_id = plan['project_id']
        result = {collection.create(plan).id for i in range(10)}
        checkpoint = collection.get(result.pop())
        checkpoint.purge()
        self.assertEqual(set(collection.list_ids(
            project_id=project_id, provider_id=provider_id)), result)

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
