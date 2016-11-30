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

from oslo_serialization import jsonutils
from oslo_versionedobjects import fields

from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.objects import base


@base.KarborObjectRegistry.register
class ScheduledOperation(base.KarborPersistentObject, base.KarborObject,
                         base.KarborObjectDictCompat,
                         base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'description': fields.StringField(nullable=True),
        'operation_type': fields.StringField(),
        'user_id': fields.StringField(),
        'project_id': fields.StringField(),
        'trigger_id': fields.UUIDField(),
        'operation_definition': fields.DictOfStringsField(),
        'enabled': fields.BooleanField(default=True),

        'trigger': fields.ObjectField("Trigger")
    }

    INSTANCE_OPTIONAL_JOINED_FIELDS = ['trigger']

    @staticmethod
    def _from_db_object(context, op, db_op, expected_attrs=[]):
        special_fields = set(['operation_definition'] +
                             op.INSTANCE_OPTIONAL_JOINED_FIELDS)

        normal_fields = set(op.fields) - special_fields
        for name in normal_fields:
            op[name] = db_op.get(name)

        op_definition = db_op['operation_definition']
        if op_definition:
            op['operation_definition'] = jsonutils.loads(op_definition)

        if 'trigger' in expected_attrs:
            if db_op.get('trigger', None) is None:
                op.trigger = None
            else:
                if not op.obj_attr_is_set('trigger'):
                    op.trigger = objects.Trigger(context)
                op.trigger._from_db_object(context, op.trigger,
                                           db_op['trigger'])

        op._context = context
        op.obj_reset_changes()
        return op

    @staticmethod
    def _convert_operation_definition_to_db_format(updates):
        op_definition = updates.pop('operation_definition', None)
        if op_definition is not None:
            updates['operation_definition'] = jsonutils.dumps(op_definition)

    @base.remotable_classmethod
    def get_by_id(cls, context, id, expected_attrs=[]):
        columns_to_join = [col for col in expected_attrs
                           if col in cls.INSTANCE_OPTIONAL_JOINED_FIELDS]

        db_op = db.scheduled_operation_get(context, id, columns_to_join)
        if db_op:
            return cls._from_db_object(context, cls(), db_op, expected_attrs)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))

        updates = self.karbor_obj_get_changes()
        self._convert_operation_definition_to_db_format(updates)
        db_op = db.scheduled_operation_create(self._context, updates)
        self._from_db_object(self._context, self, db_op)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates and self.id:
            self._convert_operation_definition_to_db_format(updates)
            db.scheduled_operation_update(self._context,
                                          self.id,
                                          updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.id:
            db.scheduled_operation_delete(self._context, self.id)


@base.KarborObjectRegistry.register
class ScheduledOperationList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('ScheduledOperation'),
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters, limit=None,
                       marker=None, sort_keys=None, sort_dirs=None):

        db_operation_list = db.scheduled_operation_get_all_by_filters_sort(
            context, filters, limit=limit, marker=marker,
            sort_keys=sort_keys, sort_dirs=sort_dirs)

        return base.obj_make_list(context, cls(context), ScheduledOperation,
                                  db_operation_list)
