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

from karbor.api.v1 import operation_logs
from karbor import context
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF


class OperationLogTest(base.TestCase):
    def setUp(self):
        super(OperationLogTest, self).setUp()
        self.controller = operation_logs.OperationLogsController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.api.v1.operation_logs.'
        'OperationLogsController._get_all')
    def test_operation_log_list_detail(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/operation_logs')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

    @mock.patch(
        'karbor.api.v1.operation_logs.'
        'OperationLogsController._get_all')
    def test_operation_log_index_limit_offset(self, mock_get_all):
        req = fakes.HTTPRequest.blank(
            '/v1/operation_logs?limit=2&offset=1')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

        req = fakes.HTTPRequest.blank('/v1/operation_logs?limit=-1&offset=1')
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

        req = fakes.HTTPRequest.blank('/v1/operation_logs?limit=a&offset=1')
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

        url = '/v1/operation_logs?limit=2&offset=43543564546567575'
        req = fakes.HTTPRequest.blank(url)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

    @mock.patch(
        'karbor.api.v1.operation_logs.'
        'OperationLogsController._operation_log_get')
    def test_operation_log_show(self, mock_get):
        req = fakes.HTTPRequest.blank('/v1/operation_logs')
        self.controller.show(req, '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')
        self.assertTrue(mock_get.called)

    def test_operation_log_show_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/operation_logs/1')
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.show,
            req, "1")
