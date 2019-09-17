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
from oslo_config import cfg
from webob import exc

from karbor.api.v1 import quotas
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF
INVALID_PROJECT_ID = '111'


class QuotaApiTest(base.TestCase):
    def setUp(self):
        super(QuotaApiTest, self).setUp()
        self.controller = quotas.QuotasController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.db.sqlalchemy.api.quota_update')
    def test_quota_update(self, mock_quota_update):
        quota = self._quota_in_request_body()
        body = {"quota": quota}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.update(
            req, '73f74f90a1754bd7ad658afb3272323f', body=body)
        self.assertTrue(mock_quota_update.called)

    def test_quota_update_with_invalid_project_id(self):
        quota = self._quota_in_request_body()
        body = {"quota": quota}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/111', use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.update,
                          req, INVALID_PROJECT_ID, body=body)

    def test_quota_update_with_invalid_type_value(self):
        body = {"quota": {"plans": "fakevalue"}}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.update,
                          req, "73f74f90a1754bd7ad658afb3272323f", body=body)

    def test_quota_update_with_invalid_num_value(self):
        body = {"quota": {"plans": -2}}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.update,
                          req, "73f74f90a1754bd7ad658afb3272323f", body=body)

    @mock.patch(
        'karbor.db.sqlalchemy.api.quota_update')
    def test_quota_update_with_zero_value(self, mock_quota_update):
        body = {"quota": {"plans": 0}}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.update(
            req, '73f74f90a1754bd7ad658afb3272323f', body=body)
        self.assertTrue(mock_quota_update.called)

    @mock.patch(
        'karbor.db.sqlalchemy.api.quota_update')
    def test_quota_update_with_invalid_key(self, mock_quota_update):
        body = {"quota": {"fakekey": 20}}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.update(
            req, '73f74f90a1754bd7ad658afb3272323f', body=body)
        self.assertEqual(0,
                         len(mock_quota_update.mock_calls))

    @mock.patch(
        'karbor.db.sqlalchemy.api.quota_create')
    @mock.patch(
        'karbor.db.sqlalchemy.api.quota_update')
    def test_quota_update_with_project_quota_not_found(self,
                                                       mock_quota_update,
                                                       mock_quota_create):
        body = {"quota": {"plans": 20}}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        mock_quota_update.side_effect = exception.ProjectQuotaNotFound
        self.controller.update(
            req, '73f74f90a1754bd7ad658afb3272323f', body=body)
        self.assertTrue(mock_quota_create.called)

    def test_quota_update_with_not_admin_context(self):
        body = {"quota": {"plans": 20}}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=False)
        self.assertRaises(
            exception.PolicyNotAuthorized, self.controller.update,
            req, "73f74f90a1754bd7ad658afb3272323f", body=body)

    @mock.patch(
        'karbor.quota.DbQuotaDriver.get_defaults')
    def test_quota_defaults(self, mock_quota_get):
        req = fakes.HTTPRequest.blank(
            'v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.defaults(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(mock_quota_get.called)

    def test_quota_defaults_with_invalid_project_id(self):
        req = fakes.HTTPRequest.blank('/v1/quotas/111',
                                      use_admin_context=True)
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.defaults,
            req, INVALID_PROJECT_ID)

    @mock.patch(
        'karbor.quota.DbQuotaDriver.get_project_quotas')
    def test_quota_detail(self, mock_quota_get):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.detail(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(mock_quota_get.called)

    def test_quota_detail_with_invalid_project_id(self):
        req = fakes.HTTPRequest.blank('/v1/quotas/111',
                                      use_admin_context=True)
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.detail,
            req, INVALID_PROJECT_ID)

    def test_quota_detail_with_project_authorize_failed(self):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=False)
        self.assertRaises(
            exc.HTTPForbidden, self.controller.detail,
            req, '73f74f90a1754bd7ad658afb3272323f')

    @mock.patch(
        'karbor.quota.DbQuotaDriver.get_project_quotas')
    def test_quota_show(self, mock_quota_get):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.show(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(mock_quota_get.called)

    def test_quota_show_invalid(self):
        req = fakes.HTTPRequest.blank('/v1/quotas/1',
                                      use_admin_context=True)
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.show,
            req, "1")

    def test_quota_show_with_project_authorize_failed(self):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=False)
        self.assertRaises(
            exc.HTTPForbidden, self.controller.show,
            req, '73f74f90a1754bd7ad658afb3272323f')

    @mock.patch(
        'karbor.quota.DbQuotaDriver.destroy_all_by_project')
    def test_quota_delete(self, mock_restore_get):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.delete(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(mock_restore_get.called)

    def test_quota_delete_with_invalid_project_id(self):
        req = fakes.HTTPRequest.blank('/v1/quotas/1',
                                      use_admin_context=True)
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.delete,
            req, "1")

    def test_quota_delete_with_non_admin_context(self):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=False)
        self.assertRaises(
            exception.PolicyNotAuthorized, self.controller.delete,
            req, "73f74f90a1754bd7ad658afb3272323f")

    def _quota_in_request_body(self):
        quota_req = {
            "plans": 20,
        }
        return quota_req
