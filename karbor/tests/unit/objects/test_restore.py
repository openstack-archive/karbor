#    Copyright 2015 SimpliVity Corp.
#
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

from karbor import objects
from karbor.tests.unit import fake_restore
from karbor.tests.unit import objects as test_objects


class TestRestore(test_objects.BaseObjectsTestCase):
    @staticmethod
    def _compare(test, db, obj):
        db = {k: v for k, v in db.items()}
        test_objects.BaseObjectsTestCase._compare(test, db, obj)

    @mock.patch('karbor.objects.Restore.get_by_id')
    def test_get_by_id(self, restore_get):
        db_restore = fake_restore.fake_db_restore()
        restore_get.return_value = db_restore
        restore = objects.Restore.get_by_id(self.context, "1")
        restore_get.assert_called_once_with(self.context, "1")
        self._compare(self, db_restore, restore)

    @mock.patch('karbor.db.sqlalchemy.api.restore_create')
    def test_create(self, restore_create):
        db_restore = fake_restore.fake_db_restore()
        restore_create.return_value = db_restore
        restore = objects.Restore(context=self.context)
        restore.create()
        self.assertEqual(db_restore['id'], restore.id)

    @mock.patch('karbor.db.sqlalchemy.api.restore_update')
    def test_save(self, restore_update):
        db_restore = fake_restore.fake_db_restore()
        restore = objects.Restore._from_db_object(
            self.context, objects.Restore(), db_restore)
        restore.status = 'FAILED'
        restore.save()
        restore_update.assert_called_once_with(self.context, restore.id,
                                               {'status': 'FAILED'})

    @mock.patch('karbor.db.sqlalchemy.api.restore_destroy')
    def test_destroy(self, restore_destroy):
        db_restore = fake_restore.fake_db_restore()
        restore = objects.Restore._from_db_object(
            self.context, objects.Restore(), db_restore)
        restore.destroy()
        self.assertTrue(restore_destroy.called)
        admin_context = restore_destroy.call_args[0][0]
        self.assertTrue(admin_context.is_admin)

    def test_obj_field_status(self):
        restore = objects.Restore(context=self.context,
                                  status='FAILED')
        self.assertEqual('FAILED', restore.status)
