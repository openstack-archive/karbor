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

from karbor import objects
from karbor.tests.unit import fake_verification
from karbor.tests.unit import objects as test_objects


class TestVerification(test_objects.BaseObjectsTestCase):
    @staticmethod
    def _compare(test, db, obj):
        db = {k: v for k, v in db.items()}
        test_objects.BaseObjectsTestCase._compare(test, db, obj)

    @mock.patch('karbor.objects.Verification.get_by_id')
    def test_get_by_id(self, verification_get):
        db_verification = fake_verification.fake_db_verification()
        verification_get.return_value = db_verification
        verification = objects.Verification.get_by_id(self.context, "1")
        verification_get.assert_called_once_with(self.context, "1")
        self._compare(self, db_verification, verification)

    @mock.patch('karbor.db.sqlalchemy.api.verification_create')
    def test_create(self, verification_create):
        db_verification = fake_verification.fake_db_verification()
        verification_create.return_value = db_verification
        verification = objects.Verification(context=self.context)
        verification.create()
        self.assertEqual(db_verification['id'], verification.id)

    @mock.patch('karbor.db.sqlalchemy.api.verification_update')
    def test_save(self, verification_update):
        db_verification = fake_verification.fake_db_verification()
        verification = objects.Verification._from_db_object(
            self.context, objects.Verification(), db_verification)
        verification.status = 'FAILED'
        verification.save()
        verification_update.assert_called_once_with(
            self.context, verification.id, {'status': 'FAILED'})

    @mock.patch('karbor.db.sqlalchemy.api.verification_destroy')
    def test_destroy(self, verification_destroy):
        db_verification = fake_verification.fake_db_verification()
        verification = objects.Verification._from_db_object(
            self.context, objects.Verification(), db_verification)
        verification.destroy()
        self.assertTrue(verification_destroy.called)
        admin_context = verification_destroy.call_args[0][0]
        self.assertTrue(admin_context.is_admin)

    def test_obj_field_status(self):
        verification = objects.Verification(context=self.context,
                                            status='FAILED')
        self.assertEqual('FAILED', verification.status)
