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

from oslo_versionedobjects import fields

from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.objects import base


@base.KarborObjectRegistry.register
class ScheduledOperationState(base.KarborPersistentObject, base.KarborObject,
                              base.KarborObjectDictCompat,
                              base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'operation_id': fields.UUIDField(),
        'service_id': fields.IntegerField(),
        'trust_id': fields.StringField(),
        'state': fields.StringField(),
        'end_time_for_run': base.DateTimeField(nullable=True),

        'operation': fields.ObjectField("ScheduledOperation")
    }

    INSTANCE_OPTIONAL_JOINED_FIELDS = ['operation']

    @staticmethod
    def _from_db_object(context, state, db_state, expected_attrs=[]):
        special_fields = set(state.INSTANCE_OPTIONAL_JOINED_FIELDS)
        normal_fields = set(state.fields) - special_fields
        for name in normal_fields:
            state[name] = db_state.get(name)

        if 'operation' in expected_attrs:
            if db_state.get('operation', None) is None:
                state.operation = None
            else:
                if not state.obj_attr_is_set('operation'):
                    state.operation = objects.ScheduledOperation(context)
                state.operation._from_db_object(context, state.operation,
                                                db_state['operation'])

        state._context = context
        state.obj_reset_changes()
        return state

    @base.remotable_classmethod
    def get_by_operation_id(cls, context, operation_id, expected_attrs=[]):
        columns_to_join = [col for col in expected_attrs
                           if col in cls.INSTANCE_OPTIONAL_JOINED_FIELDS]

        db_state = db.scheduled_operation_state_get(
            context, operation_id, columns_to_join)
        if db_state:
            return cls._from_db_object(context, cls(),
                                       db_state, columns_to_join)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))

        updates = self.karbor_obj_get_changes()
        db_state = db.scheduled_operation_state_create(self._context, updates)
        self._from_db_object(self._context, self, db_state)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates and self.operation_id:
            db.scheduled_operation_state_update(self._context,
                                                self.operation_id,
                                                updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.operation_id:
            db.scheduled_operation_state_delete(self._context,
                                                self.operation_id)


@base.KarborObjectRegistry.register
class ScheduledOperationStateList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('ScheduledOperationState'),
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters, limit=None, marker=None,
                       sort_keys=None, sort_dirs=None, columns_to_join=[]):

        option_column = ScheduledOperationState.INSTANCE_OPTIONAL_JOINED_FIELDS
        valid_columns = [column for column in columns_to_join
                         if column in option_column]

        db_state_list = db.scheduled_operation_state_get_all_by_filters_sort(
            context, filters, limit=limit, marker=marker, sort_keys=sort_keys,
            sort_dirs=sort_dirs, columns_to_join=valid_columns)

        return base.obj_make_list(
            context, cls(context), ScheduledOperationState, db_state_list,
            expected_attrs=valid_columns)
