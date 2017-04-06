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
class Plan(base.KarborPersistentObject, base.KarborObject,
           base.KarborObjectDictCompat,
           base.KarborComparableObject):
    # Version 1.0: Initial version
    VERSION = '1.0'

    OPTIONAL_FIELDS = ('resources',)

    DEFAULT_EXPECTED_ATTR = ('resources',)

    fields = {
        'id': fields.UUIDField(),
        'name': fields.StringField(),
        'description': fields.StringField(nullable=True),
        'provider_id': fields.UUIDField(),
        'project_id': fields.UUIDField(),
        'status': fields.StringField(nullable=True),
        'resources': fields.ListOfDictOfNullableStringsField(nullable=False),
        'parameters': base.DictOfDictOfStringsField(),
    }

    # obj_extra_fields is used to hold properties that are not
    # usually part of the model
    obj_extra_fields = ['plan_resources']

    def __init__(self, *args, **kwargs):
        super(Plan, self).__init__(*args, **kwargs)
        self._orig_resources = {}
        self._reset_resources_tracking()

    def obj_reset_changes(self, fields=None):
        super(Plan, self).obj_reset_changes(fields)
        self._reset_resources_tracking(fields=fields)

    def _reset_resources_tracking(self, fields=None):
        if fields is None or 'resources' in fields:
            self._orig_resources = (list(self.resources)
                                    if 'resources' in self else [])

    def obj_what_changed(self):
        changes = super(Plan, self).obj_what_changed()
        if 'resources' in self and self.resources != self._orig_resources:
            changes.add('resources')

        return changes

    @staticmethod
    def _from_db_object(context, plan, db_plan, expected_attrs=None):
        if expected_attrs is None:
            expected_attrs = []
        for name, field in plan.fields.items():
            if name in Plan.OPTIONAL_FIELDS:
                continue
            value = db_plan.get(name)
            if isinstance(field, fields.IntegerField):
                value = value or 0
            if name == "parameters" and value is not None:
                value = jsonutils.loads(value)
            plan[name] = value

        # Get data from db_plan object that was queried by joined query
        # from DB
        if 'resources' in expected_attrs:
            resources = db_plan.get('resources', [])
            resources_list = []
            for resource in resources:
                dict_temp = dict()
                dict_temp['id'] = resource['resource_id']
                dict_temp['type'] = resource['resource_type']
                dict_temp['name'] = resource['resource_name']
                dict_temp['extra_info'] = (
                    resource['resource_extra_info'])
                resources_list.append(dict_temp)
            plan.resources = resources_list

        plan._context = context
        plan.obj_reset_changes()
        return plan

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason=_('already created'))
        updates = self.karbor_obj_get_changes()

        parameters = updates.pop('parameters', None)
        if parameters is not None:
            updates['parameters'] = jsonutils.dumps(parameters)

        db_plan = db.plan_create(self._context, updates)
        kargs = {}
        if hasattr(Plan, 'DEFAULT_EXPECTED_ATTR'):
            kargs = {'expected_attrs': getattr(Plan, 'DEFAULT_EXPECTED_ATTR')}
        self._from_db_object(self._context, self, db_plan, **kargs)

    @base.remotable
    def save(self):
        updates = self.karbor_obj_get_changes()
        if updates:
            if 'parameters' in updates:
                parameters = updates.pop('parameters', None)
                if parameters is not None:
                    updates['parameters'] = jsonutils.dumps(parameters)

            if 'resources' in updates:
                resources = updates.pop('resources', None)
                resources_objlist = db.plan_resources_update(
                    self._context, self.id, resources)
                resources_dictlist = []
                for resource_obj in resources_objlist:
                    resource_dict = {}
                    resource_dict["plan_id"] = resource_obj.get("plan_id")
                    resource_dict["id"] = resource_obj.get("resource_id")
                    resource_dict["type"] = resource_obj.get("resource_type")
                    resource_dict["name"] = resource_obj.get("resource_name")
                    resource_dict["extra_info"] = resource_obj.get(
                        "resource_extra_info")
                    resources_dictlist.append(resource_dict)
                self.resources = resources_dictlist
            db.plan_update(self._context, self.id, updates)
            self.obj_reset_changes()

    @base.remotable
    def destroy(self):
        with self.obj_as_admin():
            db.plan_destroy(self._context, self.id)


@base.KarborObjectRegistry.register
class PlanList(base.ObjectListBase, base.KarborObject):
    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('Plan'),
    }

    @base.remotable_classmethod
    def get_all(cls, context, marker, limit, sort_keys=None, sort_dirs=None,
                filters=None, offset=None):
        plans = db.plan_get_all(context, marker, limit,
                                sort_keys=sort_keys, sort_dirs=sort_dirs,
                                filters=filters, offset=offset)
        expected_attrs = ['resources']
        return base.obj_make_list(context, cls(context), objects.Plan,
                                  plans, expected_attrs=expected_attrs)

    @base.remotable_classmethod
    def get_all_by_project(cls, context, project_id, marker, limit,
                           sort_keys=None, sort_dirs=None, filters=None,
                           offset=None):
        plans = db.plan_get_all_by_project(context, project_id, marker,
                                           limit, sort_keys=sort_keys,
                                           sort_dirs=sort_dirs,
                                           filters=filters, offset=offset)
        expected_attrs = ['resources']
        return base.obj_make_list(context, cls(context), objects.Plan,
                                  plans, expected_attrs=expected_attrs)
