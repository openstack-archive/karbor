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
class OperationLog(base.KarborPersistentObject, base.KarborObject,
                   base.KarborObjectDictCompat,
                   base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'project_id': fields.UUIDField(),
        'scheduled_operation_id': fields.UUIDField(),
        'started_at': base.DateTimeField(nullable=True),
        'ended_at': base.DateTimeField(nullable=True),
        'state': fields.StringField(nullable=True),
        'error': fields.StringField(nullable=True),
        'entries': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, operation_log, db_operation_log):
        for name, field in operation_log.fields.items():
            value = db_operation_log.get(name)
            if isinstance(field, fields.IntegerField):
                value = value or 0
            elif isinstance(field, fields.DateTimeField):
                value = value or None
            operation_log[name] = value

        operation_log._context = context
        operation_log.obj_reset_changes()
        return operation_log

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))
        updates = self.karbor_obj_get_changes()
        db_operation_log = db.operation_log_create(self._context, updates)
        self._from_db_object(self._context, self, db_operation_log)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates:
            db.operation_log_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        with self.obj_as_admin():
            db.operation_log_destroy(self._context, self.id)


@base.KarborObjectRegistry.register
class OperationLogList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('OperationLog'),
    }

    @base.remotable_classmethod
    def get_all(cls, context, marker, limit, sort_keys=None, sort_dirs=None,
                filters=None, offset=None):
        operation_logs = db.operation_log_get_all(context, marker, limit,
                                                  sort_keys=sort_keys,
                                                  sort_dirs=sort_dirs,
                                                  filters=filters,
                                                  offset=offset)
        return base.obj_make_list(context, cls(context), objects.OperationLog,
                                  operation_logs)

    @base.remotable_classmethod
    def get_all_by_project(cls, context, project_id, marker, limit,
                           sort_keys=None, sort_dirs=None, filters=None,
                           offset=None):
        operation_logs = db.operation_log_get_all_by_project(
            context, project_id, marker, limit, sort_keys=sort_keys,
            sort_dirs=sort_dirs, filters=filters, offset=offset)
        return base.obj_make_list(context, cls(context), objects.OperationLog,
                                  operation_logs)
