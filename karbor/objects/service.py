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
class Service(base.KarborPersistentObject, base.KarborObject,
              base.KarborObjectDictCompat,
              base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'host': fields.StringField(nullable=True),
        'binary': fields.StringField(nullable=True),
        'topic': fields.StringField(nullable=True),
        'report_count': fields.IntegerField(default=0),
        'disabled': fields.BooleanField(default=False),
        'disabled_reason': fields.StringField(nullable=True),
        'modified_at': base.DateTimeField(nullable=True),
        'rpc_current_version': fields.StringField(nullable=True),
        'rpc_available_version': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, service, db_service):
        for name, field in service.fields.items():
            value = db_service.get(name)
            if isinstance(field, fields.IntegerField):
                value = value or 0
            elif isinstance(field, fields.DateTimeField):
                value = value or None
            service[name] = value

        service._context = context
        service.obj_reset_changes()
        return service

    @base.remotable_classmethod
    def get_by_host_and_topic(cls, context, host, topic):
        db_service = db.service_get_by_host_and_topic(context, host, topic)
        return cls._from_db_object(context, cls(context), db_service)

    @base.remotable_classmethod
    def get_by_args(cls, context, host, binary_key):
        db_service = db.service_get_by_args(context, host, binary_key)
        return cls._from_db_object(context, cls(context), db_service)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))
        updates = self.karbor_obj_get_changes()
        db_service = db.service_create(self._context, updates)
        self._from_db_object(self._context, self, db_service)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates:
            db.service_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        with self.obj_as_admin():
            db.service_destroy(self._context, self.id)


@base.KarborObjectRegistry.register
class ServiceList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Service'),
    }
    child_versions = {
        '1.0': '1.0'
    }

    @base.remotable_classmethod
    def get_all(cls, context, filters=None):
        services = db.service_get_all(context, filters)
        return base.obj_make_list(context, cls(context), objects.Service,
                                  services)

    @base.remotable_classmethod
    def get_all_by_topic(cls, context, topic, disabled=None):
        services = db.service_get_all_by_topic(context, topic,
                                               disabled=disabled)
        return base.obj_make_list(context, cls(context), objects.Service,
                                  services)
