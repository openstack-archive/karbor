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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_versionedobjects import fields

from smaug import db
from smaug import exception
from smaug.i18n import _
from smaug.objects import base

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


@base.SmaugObjectRegistry.register
class ScheduledOperation(base.SmaugPersistentObject, base.SmaugObject,
                         base.SmaugObjectDictCompat,
                         base.SmaugComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'operation_type': fields.StringField(),
        'project_id': fields.StringField(),
        'trigger_id': fields.UUIDField(),
        'operation_definition': fields.StringField(),

        'trigger': fields.DictOfStringsField(),
    }

    INSTANCE_OPTIONAL_JOINED_FIELDS = ['trigger']

    @staticmethod
    def _from_db_object(context, op, db_op, expected_attrs=[]):
        for name, field in op.fields.items():
            if name in op.INSTANCE_OPTIONAL_JOINED_FIELDS:
                continue

            op[name] = db_op.get(name)

        if 'trigger' in expected_attrs:
            op['trigger'] = db_op['trigger']

        op._context = context
        op.obj_reset_changes()
        return op

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

        updates = self.smaug_obj_get_changes()
        db_op = db.scheduled_operation_create(self._context, updates)
        self._from_db_object(self._context, self, db_op)

    @base.remotable
    def save(self):
        updates = self.smaug_obj_get_changes()
        if updates and self.id:
            db.scheduled_operation_update(self._context,
                                          self.id,
                                          updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.id:
            db.scheduled_operation_delete(self._context, self.id)


@base.SmaugObjectRegistry.register
class ScheduledOperationList(base.ObjectListBase, base.SmaugObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('ScheduledOperation'),
    }
    child_versions = {
        '1.0': '1.0'
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters,
                       sort_key='created_at', sort_dir='desc', limit=None,
                       marker=None, expected_attrs=None, use_slave=False,
                       sort_keys=None, sort_dirs=None):
        pass
