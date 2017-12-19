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

from karbor.api.v1 import quota_classes
from karbor import context
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF


class QuotaClassApiTest(base.TestCase):
    def setUp(self):
        super(QuotaClassApiTest, self).setUp()
        self.controller = quota_classes.QuotaClassesController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.db.sqlalchemy.api.quota_class_update')
    def test_quota_update(self, mock_quota_update):
        quota_class = self._quota_in_request_body()
        body = {"quota_class": quota_class}
        req = fakes.HTTPRequest.blank(
            '/v1/quota_classes/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.update(
            req, '73f74f90a1754bd7ad658afb3272323f', body=body)
        self.assertTrue(mock_quota_update.called)

    @mock.patch(
        'karbor.quota.DbQuotaDriver.get_class_quotas')
    def test_quota_show(self, moak_quota_get):
        req = fakes.HTTPRequest.blank(
            '/v1/quota_classes/73f74f90a1754bd7ad658afb3272323f',
            use_admin_context=True)
        self.controller.show(
            req, '73f74f90a1754bd7ad658afb3272323f')
        self.assertTrue(moak_quota_get.called)

    def _quota_in_request_body(self):
        quota_req = {
            "plans": 20,
        }
        return quota_req
