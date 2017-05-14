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

from karbor import context
from karbor import objects
from karbor.tests.unit import objects as test_objects

NOW = timeutils.utcnow().replace(microsecond=0)

Operation_ID = '0354ca9ddcd046b693340d78759fd274'

Fake_State = {
    'created_at': NOW,
    'deleted_at': None,
    'updated_at': NOW,
    'deleted': False,
    'id': 1,
    'operation_id': Operation_ID,
    'service_id': 2,
    'trust_id': '123',
    'state': 'triggered',
}


class TestScheduledOperationState(test_objects.BaseObjectsTestCase):
    State_Class = objects.ScheduledOperationState

    @mock.patch('karbor.db.scheduled_operation_state_get')
    def test_get_by_operation_id(self, state_get):
        db_state = Fake_State
        state_get.return_value = db_state
        state = self.State_Class.get_by_operation_id(self.context,
                                                     Operation_ID)
        self._compare(self, db_state, state)
        state_get.assert_called_once_with(self.context, Operation_ID, [])

    @mock.patch('karbor.db.scheduled_operation_state_create')
    def test_create(self, state_create):
        db_state = Fake_State
        state_create.return_value = db_state
        state = self.State_Class(context=self.context)
        state.create()
        self._compare(self, db_state, state)
        state_create.assert_called_once_with(self.context, {})

    @mock.patch('karbor.db.scheduled_operation_state_update')
    def test_save(self, state_update):
        db_state = Fake_State
        state = self.State_Class._from_db_object(self.context,
                                                 self.State_Class(),
                                                 db_state)
        state.state = 'triggered'
        state.save()

        state_update.assert_called_once_with(self.context,
                                             state.operation_id,
                                             {'state': 'triggered'})

    @mock.patch('karbor.db.scheduled_operation_state_delete')
    def test_destroy(self, state_delete):
        db_state = Fake_State
        state = self.State_Class._from_db_object(self.context,
                                                 self.State_Class(),
                                                 db_state)
        state.destroy()
        state_delete.assert_called_once_with(self.context,
                                             state.operation_id)

    def test_get_state_and_operation(self):
        ctx = context.get_admin_context()
        service, trigger, operation, state = FakeEnv(ctx).do_init()

        state_obj = self.State_Class.get_by_operation_id(
            self.context, operation.id, ['operation'])

        self.assertEqual(operation.id, state_obj.operation.id)


class TestScheduledOperationStateList(test_objects.BaseObjectsTestCase):

    def setUp(self):
        super(TestScheduledOperationStateList, self).setUp()
        self.context = context.get_admin_context()

    def test_get_by_filters(self):
        service, trigger, operation, state = FakeEnv(self.context).do_init()
        states = objects.ScheduledOperationStateList.get_by_filters(
            self.context, {'service_id': service.id},
            columns_to_join=['operation'])
        self.assertEqual(1, len(states.objects))
        state1 = states.objects[0]
        self.assertEqual(state.id, state1.id)
        self.assertEqual(operation.id, state1.operation.id)


class FakeEnv(object):

    def __init__(self, ctx):
        super(FakeEnv, self).__init__()
        self.context = ctx

    def do_init(self):
        service = self._create_service()
        trigger = self._create_trigger()
        operation = self._create_operation(trigger.id)
        state = self._create_operation_state(operation.id, service.id)
        return service, trigger, operation, state

    def _create_service(self):
        service_info = {
            'host': "abc",
            'binary': 'karbor-operationengine'
        }
        service = objects.Service(self.context, **service_info)
        service.create()
        return service

    def _create_trigger(self):
        trigger_info = {
            'name': 'daily',
            'project_id': '123',
            'type': 'time',
            'properties': {}
        }
        trigger = objects.Trigger(self.context, **trigger_info)
        trigger.create()
        return trigger

    def _create_operation(self, trigger_id):
        operation_info = {
            'name': 'protect vm',
            'description': 'protect vm resource',
            'operation_type': 'protect',
            'user_id': '123',
            'project_id': '123',
            'trigger_id': trigger_id,
            'operation_definition': {}
        }
        operation = objects.ScheduledOperation(self.context, **operation_info)
        operation.create()
        return operation

    def _create_operation_state(self, operation_id, service_id):
        state_info = {
            'operation_id': operation_id,
            'service_id': service_id,
            'trust_id': '123',
            'state': 'triggered',
        }
        state = objects.ScheduledOperationState(self.context, **state_info)
        state.create()
        return state
