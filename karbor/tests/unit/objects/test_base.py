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

import datetime
import mock

from iso8601 import iso8601
from oslo_utils import uuidutils
from oslo_versionedobjects import fields

from karbor import objects
from karbor.tests.unit import objects as test_objects


@objects.base.KarborObjectRegistry.register_if(False)
class TestObject(objects.base.KarborObject):
    fields = {
        'scheduled_at': objects.base.fields.DateTimeField(nullable=True),
        'uuid': objects.base.fields.UUIDField(),
        'text': objects.base.fields.StringField(nullable=True),
    }


class TestKarborObject(test_objects.BaseObjectsTestCase):
    """Tests methods from KarborObject."""

    def setUp(self):
        super(TestKarborObject, self).setUp()
        self.obj = TestObject(
            scheduled_at=None,
            uuid=uuidutils.generate_uuid(),
            text='text')
        self.obj.obj_reset_changes()

    def test_karbor_obj_get_changes_no_changes(self):
        self.assertEqual({}, self.obj.karbor_obj_get_changes())

    def test_karbor_obj_get_changes_other_changes(self):
        self.obj.text = 'text2'
        self.assertEqual({'text': 'text2'},
                         self.obj.karbor_obj_get_changes())

    def test_karbor_obj_get_changes_datetime_no_tz(self):
        now = datetime.datetime.utcnow()
        self.obj.scheduled_at = now
        self.assertEqual({'scheduled_at': now},
                         self.obj.karbor_obj_get_changes())

    def test_karbor_obj_get_changes_datetime_tz_utc(self):
        now_tz = iso8601.parse_date('2015-06-26T22:00:01Z')
        now = now_tz.replace(tzinfo=None)
        self.obj.scheduled_at = now_tz
        self.assertEqual({'scheduled_at': now},
                         self.obj.karbor_obj_get_changes())

    def test_karbor_obj_get_changes_datetime_tz_non_utc_positive(self):
        now_tz = iso8601.parse_date('2015-06-26T22:00:01+01')
        now = now_tz.replace(tzinfo=None) - datetime.timedelta(hours=1)
        self.obj.scheduled_at = now_tz
        self.assertEqual({'scheduled_at': now},
                         self.obj.karbor_obj_get_changes())

    def test_karbor_obj_get_changes_datetime_tz_non_utc_negative(self):
        now_tz = iso8601.parse_date('2015-06-26T10:00:01-05')
        now = now_tz.replace(tzinfo=None) + datetime.timedelta(hours=5)
        self.obj.scheduled_at = now_tz
        self.assertEqual({'scheduled_at': now},
                         self.obj.karbor_obj_get_changes())

    def test_refresh(self):
        @objects.base.KarborObjectRegistry.register_if(False)
        class MyTestObject(objects.base.KarborObject,
                           objects.base.KarborObjectDictCompat,
                           objects.base.KarborComparableObject):
            fields = {'id': fields.UUIDField(),
                      'name': fields.StringField()}

        test_obj = MyTestObject(id='1', name='foo')
        refresh_obj = MyTestObject(id='1', name='bar')
        with mock.patch(
                'karbor.objects.base.KarborObject.get_by_id') as get_by_id:
            get_by_id.return_value = refresh_obj

            test_obj.refresh()
            self._compare(self, refresh_obj, test_obj)

    def test_refresh_no_id_field(self):
        @objects.base.KarborObjectRegistry.register_if(False)
        class MyTestObjectNoId(objects.base.KarborObject,
                               objects.base.KarborObjectDictCompat,
                               objects.base.KarborComparableObject):
            fields = {'uuid': fields.UUIDField()}

        test_obj = MyTestObjectNoId(uuid='1', name='foo')
        self.assertRaises(NotImplementedError, test_obj.refresh)


class TestKarborComparableObject(test_objects.BaseObjectsTestCase):
    def test_comparable_objects(self):
        @objects.base.KarborObjectRegistry.register
        class MyComparableObj(objects.base.KarborObject,
                              objects.base.KarborObjectDictCompat,
                              objects.base.KarborComparableObject):
            fields = {'foo': fields.Field(fields.Integer())}

        class NonVersionedObject(object):
            pass

        obj1 = MyComparableObj(foo=1)
        obj2 = MyComparableObj(foo=1)
        obj3 = MyComparableObj(foo=2)
        obj4 = NonVersionedObject()
        self.assertTrue(obj1 == obj2)
        self.assertFalse(obj1 == obj3)
        self.assertFalse(obj1 == obj4)
        self.assertNotEqual(obj1, None)


class TestKarborDictObject(test_objects.BaseObjectsTestCase):
    @objects.base.KarborObjectRegistry.register_if(False)
    class TestDictObject(objects.base.KarborObjectDictCompat,
                         objects.base.KarborObject):
        obj_extra_fields = ['foo']

        fields = {
            'abc': fields.StringField(nullable=True),
            'def': fields.IntegerField(nullable=True),
        }

        @property
        def foo(self):
            return 42

    def test_dict_objects(self):
        obj = self.TestDictObject()
        self.assertIsNone(obj.get('non_existing'))
        self.assertEqual('val', obj.get('abc', 'val'))
        self.assertIsNone(obj.get('abc'))
        obj.abc = 'val2'
        self.assertEqual('val2', obj.get('abc', 'val'))
        self.assertEqual(42, obj.get('foo'))

        self.assertIn('foo', obj)
        self.assertIn('abc', obj)
        self.assertNotIn('def', obj)
