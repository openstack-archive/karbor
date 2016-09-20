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
from oslo_serialization import jsonutils
from oslo_utils import timeutils

from karbor import objects
from karbor.tests.unit import objects as test_objects

NOW = timeutils.utcnow().replace(microsecond=0)

Operation_ID = '0354ca9ddcd046b693340d78759fd274'

Fake_Operation = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    'id': Operation_ID,
    'name': 'protect vm',
    'description': 'protect vm resource',
    'operation_type': 'protect',
    'user_id': '123',
    'project_id': '123',
    'trigger_id': '0354ca9ddcd046b693340d78759fd275',
    'operation_definition': '{}'
}


class TestScheduledOperation(test_objects.BaseObjectsTestCase):
    Operation_Class = objects.ScheduledOperation

    @mock.patch('karbor.db.scheduled_operation_get')
    def test_get_by_id(self, operation_get):
        db_op = Fake_Operation.copy()
        operation_get.return_value = db_op

        op = self.Operation_Class.get_by_id(self.context, Operation_ID)
        db_op['operation_definition'] = jsonutils.loads(
            db_op['operation_definition'])
        self._compare(self, db_op, op)
        operation_get.assert_called_once_with(self.context, Operation_ID, [])

    @mock.patch('karbor.db.scheduled_operation_get')
    def test_get_join_trigger(self, operation_get):
        db_op = Fake_Operation.copy()
        db_op['trigger'] = {
            'created_at': NOW,
            'deleted_at': None,
            'updated_at': NOW,
            'deleted': False,
            'id': '123',
            'name': 'daily',
            'project_id': '123',
            'type': 'time',
            'properties': '{}'
        }
        operation_get.return_value = db_op

        op = self.Operation_Class.get_by_id(self.context,
                                            Operation_ID, ['trigger'])
        db_op['operation_definition'] = jsonutils.loads(
            db_op['operation_definition'])
        self.assertEqual(db_op['trigger']['type'], op.trigger.type)
        operation_get.assert_called_once_with(self.context,
                                              Operation_ID, ['trigger'])

    @mock.patch('karbor.db.scheduled_operation_create')
    def test_create(self, operation_create):
        db_op = Fake_Operation.copy()
        operation_create.return_value = db_op

        op = self.Operation_Class(context=self.context)
        op.create()
        db_op['operation_definition'] = jsonutils.loads(
            db_op['operation_definition'])
        self._compare(self, db_op, op)
        operation_create.assert_called_once_with(self.context, {})

    @mock.patch('karbor.db.scheduled_operation_update')
    def test_save(self, operation_update):
        db_op = Fake_Operation
        op = self.Operation_Class._from_db_object(self.context,
                                                  self.Operation_Class(),
                                                  db_op)
        fake_op_def = {'a': '1'}
        op.name = 'protect volume'
        op.operation_definition = fake_op_def
        op.save()

        operation_update.assert_called_once_with(
            self.context, op.id,
            {'name': 'protect volume',
             'operation_definition': jsonutils.dumps(fake_op_def)})

    @mock.patch('karbor.db.scheduled_operation_delete')
    def test_destroy(self, operation_delete):
        db_op = Fake_Operation
        op = self.Operation_Class._from_db_object(self.context,
                                                  self.Operation_Class(),
                                                  db_op)
        op.destroy()
        operation_delete.assert_called_once_with(self.context, op.id)
