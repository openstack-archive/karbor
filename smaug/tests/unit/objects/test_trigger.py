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

from smaug import objects
from smaug.tests.unit import objects as test_objects

NOW = timeutils.utcnow().replace(microsecond=0)

Trigger_ID = '0354ca9ddcd046b693340d78759fd274'

Fake_Trigger = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    'id': Trigger_ID,
    'name': 'daily',
    'project_id': '123',
    'type': 'time',
    'properties': '{}'
}


class TestTrigger(test_objects.BaseObjectsTestCase):
    Trigger_Class = objects.Trigger

    @mock.patch('smaug.db.trigger_get')
    def test_get_by_id(self, trigger_get):
        db_trigger = Fake_Trigger
        trigger_get.return_value = db_trigger

        trigger = self.Trigger_Class.get_by_id(self.context, Trigger_ID)
        self._compare(self, db_trigger, trigger)
        trigger_get.assert_called_once_with(self.context, Trigger_ID)

    @mock.patch('smaug.db.trigger_create')
    def test_create(self, trigger_create):
        db_trigger = Fake_Trigger
        trigger_create.return_value = db_trigger

        trigger = self.Trigger_Class(context=self.context)
        trigger.create()
        self._compare(self, db_trigger, trigger)
        trigger_create.assert_called_once_with(self.context, {})

    @mock.patch('smaug.db.trigger_update')
    def test_save(self, trigger_update):
        db_trigger = Fake_Trigger
        trigger = self.Trigger_Class._from_db_object(self.context,
                                                     self.Trigger_Class(),
                                                     db_trigger)
        trigger.name = 'weekly'
        trigger.save()

        trigger_update.assert_called_once_with(self.context,
                                               trigger.id,
                                               {'name': 'weekly'})

    @mock.patch('smaug.db.trigger_delete')
    def test_destroy(self, trigger_delete):
        db_trigger = Fake_Trigger
        trigger = self.Trigger_Class._from_db_object(self.context,
                                                     self.Trigger_Class(),
                                                     db_trigger)
        trigger.destroy()
        trigger_delete.assert_called_once_with(self.context, trigger.id)
