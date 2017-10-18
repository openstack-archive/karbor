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
import six

from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.objects import base


@base.KarborObjectRegistry.register
class Verification(base.KarborPersistentObject, base.KarborObject,
                   base.KarborObjectDictCompat,
                   base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'project_id': fields.UUIDField(),
        'provider_id': fields.UUIDField(),
        'checkpoint_id': fields.UUIDField(),
        'parameters': base.DictOfDictOfStringsField(nullable=True),
        'status': fields.StringField(nullable=True),
        'resources_status': fields.DictOfStringsField(nullable=True),
        'resources_reason': fields.DictOfStringsField(nullable=True),
    }

    json_fields = ('parameters', 'resources_status', 'resources_reason')

    @classmethod
    def _from_db_object(cls, context, verification, db_verification):
        for name, field in verification.fields.items():
            value = db_verification.get(name)
            if isinstance(field, fields.IntegerField):
                value = value or 0
            elif isinstance(field, fields.DateTimeField):
                value = value or None
            if name in cls.json_fields:
                value = jsonutils.loads(value) if value else {}
            verification[name] = value

        verification._context = context
        verification.obj_reset_changes()
        return verification

    @classmethod
    def _convert_properties_to_db_format(cls, updates):
        for attr in cls.json_fields:
            value = updates.pop(attr, None)
            if value:
                updates[attr] = jsonutils.dumps(value)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))
        updates = self.karbor_obj_get_changes()
        self._convert_properties_to_db_format(updates)
        db_verification = db.verification_create(self._context, updates)
        self._from_db_object(self._context, self, db_verification)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        self._convert_properties_to_db_format(updates)
        if updates:
            db.verification_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        with self.obj_as_admin():
            db.verification_destroy(self._context, self.id)

    @base.remotable
    def update_resource_status(self, resource_type, resource_id, status,
                               reason=None):
        key = '{}#{}'.format(resource_type, resource_id)
        if not self.obj_attr_is_set('resources_status'):
            self.resources_status = {}
        self.resources_status[key] = status
        self._changed_fields.add('resources_status')
        if isinstance(reason, six.string_types):
            if not self.obj_attr_is_set('resources_reason'):
                self.resources_reason = {}
            self.resources_reason[key] = reason
            self._changed_fields.add('resources_reason')


@base.KarborObjectRegistry.register
class VerificationList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Verification'),
    }

    @base.remotable_classmethod
    def get_all(cls, context, marker, limit, sort_keys=None, sort_dirs=None,
                filters=None, offset=None):
        verifications = db.verification_get_all(context, marker, limit,
                                                sort_keys=sort_keys,
                                                sort_dirs=sort_dirs,
                                                filters=filters, offset=offset)
        return base.obj_make_list(context, cls(context), objects.Verification,
                                  verifications)

    @base.remotable_classmethod
    def get_all_by_project(cls, context, project_id, marker, limit,
                           sort_keys=None, sort_dirs=None, filters=None,
                           offset=None):
        verifications = db.verification_get_all_by_project(
            context, project_id, marker,
            limit, sort_keys=sort_keys,
            sort_dirs=sort_dirs,
            filters=filters,
            offset=offset)
        return base.obj_make_list(context, cls(context), objects.Verification,
                                  verifications)
