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

from karbor import exception
from karbor import objects
from karbor.tests.unit import objects as test_objects

NOW = timeutils.utcnow().replace(microsecond=0)

Log_ID = 0

Fake_Log = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    'id': Log_ID,
    'operation_id': '123',
    'expect_start_time': NOW,
    'triggered_time': NOW,
    'actual_start_time': NOW,
    'end_time': NOW,
    'state': 'in_progress',
    'extend_info': '',
}


class TestScheduledOperationLog(test_objects.BaseObjectsTestCase):
    def setUp(self):
        super(TestScheduledOperationLog, self).setUp()

        self.log_class = objects.ScheduledOperationLog
        self.db_log = Fake_Log

    @mock.patch('karbor.db.scheduled_operation_log_get')
    def test_get_by_id(self, log_get):
        log_get.return_value = self.db_log

        log = self.log_class.get_by_id(self.context, Log_ID)
        self._compare(self, self.db_log, log)
        log_get.assert_called_once_with(self.context, Log_ID)

    def test_get_by_no_existing_id(self):
        self.assertRaises(exception.ScheduledOperationLogNotFound,
                          self.log_class.get_by_id,
                          self.context, Log_ID)

    @mock.patch('karbor.db.scheduled_operation_log_create')
    def test_create(self, log_create):
        log_create.return_value = self.db_log

        log = self.log_class(context=self.context)
        log.create()
        self._compare(self, self.db_log, log)
        log_create.assert_called_once_with(self.context, {})

        self.assertRaises(exception.ObjectActionError,
                          log.create)

    @mock.patch('karbor.db.scheduled_operation_log_update')
    def test_save(self, log_update):
        log = self.log_class._from_db_object(self.context,
                                             self.log_class(),
                                             self.db_log)
        log.state = 'success'
        log.save()

        log_update.assert_called_once_with(self.context,
                                           log.id,
                                           {'state': 'success'})

    @mock.patch('karbor.db.scheduled_operation_log_delete')
    def test_destroy(self, log_delete):
        log = self.log_class._from_db_object(self.context,
                                             self.log_class(),
                                             self.db_log)
        log.destroy()
        log_delete.assert_called_once_with(self.context, log.id)


class TestScheduledOperationLogList(test_objects.BaseObjectsTestCase):

    def test_get_by_filters(self):
        log = self._create_operation_log('123')

        logs = objects.ScheduledOperationLogList.get_by_filters(
            self.context, {'state': ['in_progress']})
        self.assertEqual(1, len(logs.objects))
        log1 = logs.objects[0]
        self.assertEqual(log.id, log1.id)

    def _create_operation_log(self, operation_id):
        log_info = {
            'operation_id': operation_id,
            'state': 'in_progress',
        }
        log = objects.ScheduledOperationLog(self.context, **log_info)
        log.create()
        return log
