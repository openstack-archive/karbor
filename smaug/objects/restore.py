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
from oslo_serialization import jsonutils
from oslo_versionedobjects import fields

from smaug import db
from smaug import exception
from smaug.i18n import _
from smaug import objects
from smaug.objects import base

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


@base.SmaugObjectRegistry.register
class Restore(base.SmaugPersistentObject, base.SmaugObject,
              base.SmaugObjectDictCompat,
              base.SmaugComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'project_id': fields.UUIDField(),
        'provider_id': fields.UUIDField(),
        'checkpoint_id': fields.UUIDField(),
        'restore_target': fields.StringField(nullable=True),
        'parameters': fields.DictOfStringsField(nullable=True),
        'status': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, restore, db_restore):
        for name, field in restore.fields.items():
            value = db_restore.get(name)
            if isinstance(field, fields.IntegerField):
                value = value or 0
            elif isinstance(field, fields.DateTimeField):
                value = value or None
            if name == "parameters" and value is not None:
                value = jsonutils.loads(value)
            restore[name] = value

        restore._context = context
        restore.obj_reset_changes()
        return restore

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))
        updates = self.smaug_obj_get_changes()

        parameters = updates.pop('parameters', None)
        if parameters is not None:
            updates['parameters'] = jsonutils.dumps(parameters)

        db_restore = db.restore_create(self._context, updates)
        self._from_db_object(self._context, self, db_restore)

    @base.remotable
    def save(self):
        updates = self.smaug_obj_get_changes()
        if updates:
            db.restore_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        with self.obj_as_admin():
            db.restore_destroy(self._context, self.id)


@base.SmaugObjectRegistry.register
class RestoreList(base.ObjectListBase, base.SmaugObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Restore'),
    }

    @base.remotable_classmethod
    def get_all(cls, context, marker, limit, sort_keys=None, sort_dirs=None,
                filters=None, offset=None):
        restores = db.restore_get_all(context, marker, limit,
                                      sort_keys=sort_keys, sort_dirs=sort_dirs,
                                      filters=filters, offset=offset)
        return base.obj_make_list(context, cls(context), objects.Restore,
                                  restores)

    @base.remotable_classmethod
    def get_all_by_project(cls, context, project_id, marker, limit,
                           sort_keys=None, sort_dirs=None, filters=None,
                           offset=None):
        restores = db.restore_get_all_by_project(context, project_id, marker,
                                                 limit, sort_keys=sort_keys,
                                                 sort_dirs=sort_dirs,
                                                 filters=filters,
                                                 offset=offset)
        return base.obj_make_list(context, cls(context), objects.Restore,
                                  restores)
