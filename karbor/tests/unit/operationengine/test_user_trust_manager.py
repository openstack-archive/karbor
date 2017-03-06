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

from karbor import context
from karbor.services.operationengine import user_trust_manager
from karbor.tests import base


G_TOKEN_ID = 'abcdefg'
G_TRUST_ID = '1234556'


class FakeSession(object):
    def get_token(self):
        return G_TOKEN_ID


class FakeSKP(object):
    def create_trust_to_karbor(self, context):
        return G_TRUST_ID

    def delete_trust_to_karbor(self, trust_id):
        return

    def create_trust_session(self, trust_id):
        return FakeSession()


class UserTrustManagerTestCase(base.TestCase):
    """Test cases for UserTrustManager class."""

    def setUp(self):
        super(UserTrustManagerTestCase, self).setUp()

        self._user_id = '123'
        self._project_id = '456'
        self._ctx = context.RequestContext(user_id=self._user_id,
                                           project_id=self._project_id)
        self._manager = user_trust_manager.UserTrustManager()
        self._manager._skp = FakeSKP()

    def test_add_operation(self):
        manager = self._manager
        operation_id = 'abc'
        self.assertEqual(G_TRUST_ID, manager.add_operation(
            self._ctx, operation_id))

        info = manager._get_user_trust_info(self._user_id, self._project_id)
        self.assertIn(operation_id, info['operation_ids'])

        manager.add_operation(self._ctx, operation_id)
        self.assertEqual(1, len(info['operation_ids']))

    @mock.patch.object(FakeSKP, 'delete_trust_to_karbor')
    def test_delete_operation(self, del_trust):
        manager = self._manager
        op_ids = ['abc', '123']
        for op_id in op_ids:
            manager.add_operation(self._ctx, op_id)

        info = manager._get_user_trust_info(self._user_id, self._project_id)
        self.assertEqual(2, len(info['operation_ids']))

        manager.delete_operation(self._ctx, op_ids[0])
        self.assertEqual(1, len(info['operation_ids']))

        manager.delete_operation(self._ctx, op_ids[1])
        self.assertEqual(0, len(info['operation_ids']))
        del_trust.assert_called_once_with(G_TRUST_ID)

    def test_resume_operation(self):
        manager = self._manager
        operation_id = 'abc'
        manager.resume_operation(operation_id, self._user_id,
                                 self._project_id, G_TRUST_ID)

        info = manager._get_user_trust_info(self._user_id, self._project_id)
        self.assertIn(operation_id, info['operation_ids'])

        manager.resume_operation(operation_id, self._user_id,
                                 self._project_id, G_TRUST_ID)
        self.assertEqual(1, len(info['operation_ids']))

    def test_get_token(self):
        manager = self._manager
        manager.add_operation(self._ctx, 'abc')

        self.assertEqual(G_TOKEN_ID, manager.get_token(
            self._user_id, self._project_id))
