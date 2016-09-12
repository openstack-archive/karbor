#    Licensed under the Apache License, Version 2.0 (the "License"); you may
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
from oslo_utils import timeutils

from karbor import objects
from karbor.tests.unit import objects as test_objects

NOW = timeutils.utcnow().replace(microsecond=0)

CheckpointRecord_ID = '36ea41b2-c358-48a7-9117-70cb7617410a'

Fake_CheckpointRecord = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    "id": CheckpointRecord_ID,
    "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
    "checkpoint_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
    "checkpoint_status": "available",
    "provider_id": "39bb894794b741e982bd26144d2949f6",
    "plan_id": "efc6a88b-9096-4bb6-8634-cda182a6e12b",
    "operation_id": "64e51e85-4f31-441f-9a5d-6e93e3196628",
    "create_by": "operation-engine",
    "extend_info": "[{"
                    "'id': '0354ca9d-dcd0-46b6-9334-0d78759fd275',"
                    "'type': 'OS::Nova::Server',"
                    "'name': 'vm1'"
                    "}]"
}


class TestCheckpointRecord(test_objects.BaseObjectsTestCase):
    CheckpointRecord_Class = objects.CheckpointRecord

    @mock.patch('karbor.db.checkpoint_record_get')
    def test_get_by_id(self, checkpoint_record_get):
        db_checkpoint_record = Fake_CheckpointRecord.copy()
        checkpoint_record_get.return_value = db_checkpoint_record

        checkpoint_record = self.CheckpointRecord_Class.get_by_id(
            self.context,
            CheckpointRecord_ID)
        self._compare(self, db_checkpoint_record, checkpoint_record)
        checkpoint_record_get.assert_called_once_with(
            self.context,
            CheckpointRecord_ID)

    @mock.patch('karbor.db.checkpoint_record_create')
    def test_create(self, checkpoint_record_create):
        db_checkpoint_record = Fake_CheckpointRecord.copy()
        checkpoint_record_create.return_value = db_checkpoint_record

        checkpoint_record = self.CheckpointRecord_Class(context=self.context)
        checkpoint_record.create()
        self._compare(self, db_checkpoint_record, checkpoint_record)
        checkpoint_record_create.assert_called_once_with(self.context, {})

    @mock.patch('karbor.db.checkpoint_record_update')
    def test_save(self, checkpoint_record_update):
        db_checkpoint_record = Fake_CheckpointRecord
        checkpoint_record = self.CheckpointRecord_Class._from_db_object(
            self.context,
            self.CheckpointRecord_Class(),
            db_checkpoint_record)
        checkpoint_record.checkpoint_status = 'error'
        checkpoint_record.save()

        checkpoint_record_update.assert_called_once_with(
            self.context,
            checkpoint_record.id,
            {'checkpoint_status': 'error'})

    @mock.patch('karbor.db.checkpoint_record_destroy')
    def test_destroy(self, checkpoint_record_destroy):
        db_checkpoint_record = Fake_CheckpointRecord
        checkpoint_record = self.CheckpointRecord_Class._from_db_object(
            self.context,
            self.CheckpointRecord_Class(),
            db_checkpoint_record)
        checkpoint_record.destroy()
        checkpoint_record_destroy.assert_called_once_with(
            self.context,
            checkpoint_record.id)
