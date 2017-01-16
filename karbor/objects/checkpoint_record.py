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
from oslo_versionedobjects import fields

from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor.objects import base

CONF = cfg.CONF


@base.KarborObjectRegistry.register
class CheckpointRecord(base.KarborPersistentObject, base.KarborObject,
                       base.KarborObjectDictCompat,
                       base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'project_id': fields.UUIDField(),
        'checkpoint_id': fields.UUIDField(),
        'checkpoint_status': fields.StringField(),
        'provider_id': fields.UUIDField(),
        'plan_id': fields.UUIDField(),
        'operation_id': fields.StringField(nullable=True),
        'create_by': fields.StringField(nullable=True),
        'extend_info': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, checkpoint_record, db_checkpoint_record):
        for name, field in checkpoint_record.fields.items():
            checkpoint_record[name] = db_checkpoint_record.get(name)

        checkpoint_record._context = context
        checkpoint_record.obj_reset_changes()
        return checkpoint_record

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_checkpoint_record = db.checkpoint_record_get(context, id)
        if db_checkpoint_record:
            return cls._from_db_object(context, cls(), db_checkpoint_record)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))
        updates = self.karbor_obj_get_changes()
        db_checkpoint_record = db.checkpoint_record_create(self._context,
                                                           updates)
        self._from_db_object(self._context, self, db_checkpoint_record)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates and self.id:
            db.checkpoint_record_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.id:
            db.checkpoint_record_destroy(self._context, self.id)


@base.KarborObjectRegistry.register
class CheckpointRecordList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('CheckpointRecord'),
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters, limit=None,
                       marker=None, sort_keys=None, sort_dirs=None):

        checkpoint_record_list = db.checkpoint_record_get_all_by_filters_sort(
            context, filters, limit=limit, marker=marker,
            sort_keys=sort_keys, sort_dirs=sort_dirs)

        return base.obj_make_list(context,
                                  cls(context),
                                  CheckpointRecord,
                                  checkpoint_record_list)
