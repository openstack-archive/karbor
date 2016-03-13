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
class Trigger(base.SmaugPersistentObject, base.SmaugObject,
              base.SmaugObjectDictCompat,
              base.SmaugComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'project_id': fields.StringField(),
        'type': fields.StringField(),
        'properties': fields.StringField(),
    }

    @staticmethod
    def _from_db_object(context, trigger, db_trigger):
        for name, field in trigger.fields.items():
            trigger[name] = db_trigger.get(name)

        trigger._context = context
        trigger.obj_reset_changes()
        return trigger

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_trigger = db.trigger_get(context, id)
        if db_trigger:
            return cls._from_db_object(context, cls(), db_trigger)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))

        updates = self.smaug_obj_get_changes()
        db_trigger = db.trigger_create(self._context, updates)
        self._from_db_object(self._context, self, db_trigger)

    @base.remotable
    def save(self):
        updates = self.smaug_obj_get_changes()
        if updates and self.id:
            db.trigger_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.id:
            db.trigger_delete(self._context, self.id)


@base.SmaugObjectRegistry.register
class TriggerList(base.ObjectListBase, base.SmaugObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Trigger'),
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
