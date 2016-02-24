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
class ScheduledOperationLog(base.SmaugPersistentObject, base.SmaugObject,
                            base.SmaugObjectDictCompat,
                            base.SmaugComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'operation_id': fields.UUIDField(),
        'expect_start_time': fields.DateTimeField(nullable=True),
        'triggered_time': fields.DateTimeField(nullable=True),
        'actual_start_time': fields.DateTimeField(nullable=True),
        'end_time': fields.DateTimeField(nullable=True),
        'state': fields.StringField(),
        'extend_info': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, log, db_log):
        for name, field in log.fields.items():
            log[name] = db_log.get(name)

        log._context = context
        log.obj_reset_changes()
        return log

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_log = db.scheduled_operation_log_get(context, id)
        if db_log:
            return cls._from_db_object(context, cls(), db_log)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))

        updates = self.smaug_obj_get_changes()
        db_log = db.scheduled_operation_log_create(self._context, updates)
        self._from_db_object(self._context, self, db_log)

    @base.remotable
    def save(self):
        updates = self.smaug_obj_get_changes()
        if updates and self.id is not None:
            db.scheduled_operation_log_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.id is not None:
            db.scheduled_operation_log_delete(self._context, self.id)
