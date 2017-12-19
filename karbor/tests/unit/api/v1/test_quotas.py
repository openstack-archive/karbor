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
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF


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

    def test_quota_update_invalid_project_id(self):
        quota = self._quota_in_request_body()
        body = {"quota": quota}
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/111', use_admin_context=True)
        self.assertRaises(exc.HTTPBadRequest, self.controller.update,
                          req, '111', body=body)

    @mock.patch(
        'karbor.quota.DbQuotaDriver.get_project_quotas')
    def test_quota_show(self, moak_quota_get):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.show(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(moak_quota_get.called)

    def test_quota_show_invalid(self):
        req = fakes.HTTPRequest.blank('/v1/quotas/1',
                                      use_admin_context=True)
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.show,
            req, "1")

    @mock.patch(
        'karbor.quota.DbQuotaDriver.destroy_all_by_project')
    def test_quota_delete(self, moak_restore_get):
        req = fakes.HTTPRequest.blank(
            '/v1/quotas/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.delete(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(moak_restore_get.called)

    def test_quota_delete_invalid(self):
        req = fakes.HTTPRequest.blank('/v1/quotas/1',
                                      use_admin_context=True)
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.delete,
            req, "1")

    def _quota_in_request_body(self):
        quota_req = {
            "plans": 20,
        }
        return quota_req
