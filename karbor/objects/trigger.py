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
from karbor.objects import base


@base.KarborObjectRegistry.register
class Trigger(base.KarborPersistentObject, base.KarborObject,
              base.KarborObjectDictCompat,
              base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'project_id': fields.StringField(),
        'type': fields.StringField(),
        'properties': fields.DictOfStringsField(),
    }

    @staticmethod
    def _from_db_object(context, trigger, db_trigger):
        special_fields = set(['properties'])

        normal_fields = set(trigger.fields) - special_fields
        for name in normal_fields:
            trigger[name] = db_trigger.get(name)

        properties = db_trigger['properties']
        if properties:
            trigger['properties'] = jsonutils.loads(properties)

        trigger._context = context
        trigger.obj_reset_changes()
        return trigger

    @staticmethod
    def _convert_properties_to_db_format(updates):
        properties = updates.pop('properties', None)
        if properties is not None:
            updates['properties'] = jsonutils.dumps(properties)

    @base.remotable_classmethod
    def get_by_id(cls, context, id):
        db_trigger = db.trigger_get(context, id)
        if db_trigger:
            return cls._from_db_object(context, cls(), db_trigger)

    @base.remotable
    def create(self):
        updates = self.karbor_obj_get_changes()
        self._convert_properties_to_db_format(updates)
        db_trigger = db.trigger_create(self._context, updates)
        self._from_db_object(self._context, self, db_trigger)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates and self.id:
            self._convert_properties_to_db_format(updates)
            db.trigger_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        if self.id:
            db.trigger_delete(self._context, self.id)


@base.KarborObjectRegistry.register
class TriggerList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Trigger'),
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters, limit=None,
                       marker=None, sort_keys=None, sort_dirs=None):

        db_trigger_list = db.trigger_get_all_by_filters_sort(
            context, filters, limit=limit, marker=marker,
            sort_keys=sort_keys, sort_dirs=sort_dirs)

        return base.obj_make_list(context, cls(context), Trigger,
                                  db_trigger_list)
