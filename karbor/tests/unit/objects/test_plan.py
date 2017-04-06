#    Copyright 2015 SimpliVity Corp.
#
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

import mock

from oslo_serialization import jsonutils

from karbor import objects
from karbor.tests.unit import fake_plan
from karbor.tests.unit import objects as test_objects


class TestPlan(test_objects.BaseObjectsTestCase):
    @staticmethod
    def _compare(test, db, obj):
        db = {k: v for k, v in db.items()
              if not k.endswith('resources')}
        test_objects.BaseObjectsTestCase._compare(test, db, obj)

    @mock.patch('karbor.objects.Plan.get_by_id')
    def test_get_by_id(self, plan_get):
        db_plan = fake_plan.fake_db_plan()
        plan_get.return_value = db_plan
        plan = objects.Plan.get_by_id(self.context, "1")
        plan_get.assert_called_once_with(self.context, "1")
        self._compare(self, db_plan, plan)

    @mock.patch('karbor.db.sqlalchemy.api.plan_create')
    def test_create(self, plan_create):
        db_plan = fake_plan.fake_db_plan()
        plan_create.return_value = db_plan
        plan = objects.Plan(context=self.context)
        plan.create()
        self.assertEqual(db_plan['id'], plan.id)

    @mock.patch('karbor.db.sqlalchemy.api.plan_update')
    def test_save(self, plan_update):
        db_plan = fake_plan.fake_db_plan()
        plan = objects.Plan._from_db_object(self.context,
                                            objects.Plan(), db_plan)
        plan.name = 'planname'
        plan.save()
        plan_update.assert_called_once_with(self.context, plan.id,
                                            {'name': 'planname'})

    @mock.patch('karbor.db.sqlalchemy.api.plan_resources_update',
                return_value=[
                    {'resource_id': 'key1',
                     "resource_type": "value1",
                     "extra_info": "{'availability_zone': 'az1'}"}
                ])
    @mock.patch('karbor.db.sqlalchemy.api.plan_update')
    def test_save_with_resource(self, plan_update, resource_update):
        db_plan = fake_plan.fake_db_plan()
        plan = objects.Plan._from_db_object(self.context,
                                            objects.Plan(), db_plan)
        plan.name = 'planname'
        plan.resources = [{'id': 'key1',
                           "type": "value1",
                           "extra_info": "{'availability_zone': 'az1'}"}]
        self.assertEqual({'name': 'planname',
                          'resources': [{'id': 'key1',
                                         "type": "value1",
                                         "extra_info":
                                             "{'availability_zone': 'az1'}"}]},
                         plan.obj_get_changes())
        plan.save()
        plan_update.assert_called_once_with(self.context, plan.id,
                                            {'name': 'planname'})
        resource_update.assert_called_once_with(
            self.context, plan.id, [{'id': 'key1', "type": "value1",
                                     "extra_info":
                                         "{'availability_zone': 'az1'}"}])

    @mock.patch('karbor.db.sqlalchemy.api.plan_destroy')
    def test_destroy(self, plan_destroy):
        db_plan = fake_plan.fake_db_plan()
        plan = objects.Plan._from_db_object(self.context,
                                            objects.Plan(), db_plan)
        plan.destroy()
        self.assertTrue(plan_destroy.called)
        admin_context = plan_destroy.call_args[0][0]
        self.assertTrue(admin_context.is_admin)

    def test_parameters(self):
        db_plan = fake_plan.fake_db_plan()
        plan = objects.Plan._from_db_object(self.context,
                                            objects.Plan(), db_plan)
        self.assertEqual(plan.parameters,
                         jsonutils.loads(fake_plan.db_plan['parameters']))

    def test_obj_fields(self):
        plan = objects.Plan(context=self.context, id="2", name="testname")
        self.assertEqual(['plan_resources'], plan.obj_extra_fields)
        self.assertEqual('testname', plan.name)
        self.assertEqual('2', plan.id)

    def test_obj_field_status(self):
        plan = objects.Plan(context=self.context,
                            status='suspending')
        self.assertEqual('suspending', plan.status)
