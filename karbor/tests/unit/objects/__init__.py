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

from oslo_utils import timeutils
from oslo_versionedobjects import fields

from karbor import context
from karbor.objects import base as obj_base
from karbor.tests import base


class BaseObjectsTestCase(base.TestCase):
    def setUp(self):
        super(BaseObjectsTestCase, self).setUp()
        self.user_id = 'fake-user'
        self.project_id = 'fake-project'
        self.context = context.RequestContext(self.user_id, self.project_id,
                                              is_admin=False)
        # We only test local right now.
        self.assertIsNone(obj_base.KarborObject.indirection_api)

    @staticmethod
    def _compare(test, db, obj):
        for field, value in db.items():
            if not hasattr(obj, field):
                continue

            if (isinstance(obj.fields[field], fields.DateTimeField) and
               db[field]):
                test.assertEqual(db[field],
                                 timeutils.normalize_time(obj[field]))
            elif isinstance(obj[field], obj_base.ObjectListBase):
                test.assertEqual(db[field], obj[field].objects)
            else:
                test.assertEqual(db[field], obj[field])
