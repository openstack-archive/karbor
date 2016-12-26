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
from karbor.tests.unit import fake_operation_log
from karbor.tests.unit import objects as test_objects


class TestOperationLog(test_objects.BaseObjectsTestCase):
    @staticmethod
    def _compare(test, db, obj):
        db = {k: v for k, v in db.items()}
        test_objects.BaseObjectsTestCase._compare(test, db, obj)

    @mock.patch('karbor.objects.OperationLog.get_by_id')
    def test_get_by_id(self, operation_log_get):
        db_operation_log = fake_operation_log.fake_db_operation_log()
        operation_log_get.return_value = db_operation_log
        operation_log = objects.OperationLog.get_by_id(self.context, "1")
        operation_log_get.assert_called_once_with(self.context, "1")
        self._compare(self, db_operation_log, operation_log)

    @mock.patch('karbor.db.sqlalchemy.api.operation_log_create')
    def test_create(self, operation_log_create):
        db_operation_log = fake_operation_log.fake_db_operation_log()
        operation_log_create.return_value = db_operation_log
        operation_log = objects.OperationLog(context=self.context)
        operation_log.create()
        self.assertEqual(db_operation_log['id'], operation_log.id)

    @mock.patch('karbor.db.sqlalchemy.api.operation_log_update')
    def test_save(self, operation_log_update):
        db_operation_log = fake_operation_log.fake_db_operation_log()
        operation_log = objects.OperationLog._from_db_object(
            self.context, objects.OperationLog(), db_operation_log)
        operation_log.state = 'finished'
        operation_log.save()
        operation_log_update.assert_called_once_with(
            self.context, operation_log.id, {'state': 'finished'})

    @mock.patch('karbor.db.sqlalchemy.api.operation_log_destroy')
    def test_destroy(self, operation_log_destroy):
        db_operation_log = fake_operation_log.fake_db_operation_log()
        operation_log = objects.OperationLog._from_db_object(
            self.context, objects.OperationLog(), db_operation_log)
        operation_log.destroy()
        self.assertTrue(operation_log_destroy.called)
        admin_context = operation_log_destroy.call_args[0][0]
        self.assertTrue(admin_context.is_admin)

    def test_obj_field_status(self):
        operation_log = objects.OperationLog(context=self.context,
                                             state='finished')
        self.assertEqual('finished', operation_log.state)
