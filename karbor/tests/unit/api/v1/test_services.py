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
from mock import mock
from webob import exc

from karbor.api.v1 import services
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes


class ServiceApiTest(base.TestCase):
    def setUp(self):
        super(ServiceApiTest, self).setUp()
        self.controller = services.ServiceController()

    @mock.patch('karbor.objects.service.ServiceList.get_all_by_args')
    def test_service_list_with_admin_context(self, mock_get_all_by_args):
        req = fakes.HTTPRequest.blank('/v1/os-services?host=host1',
                                      use_admin_context=True)
        self.controller.index(req)
        self.assertTrue(mock_get_all_by_args.called)

    def test_service_list_with_non_admin_context(self):
        req = fakes.HTTPRequest.blank('/v1/os-services',
                                      use_admin_context=False)
        self.assertRaises(
            exception.PolicyNotAuthorized, self.controller.index, req)

    @mock.patch('karbor.objects.service.ServiceList.get_all_by_args')
    def test_service_list_with_invalid_services(self, mock_get_all_by_args):
        req = fakes.HTTPRequest.blank('/v1/os-services',
                                      use_admin_context=True)
        mock_get_all_by_args.side_effect = exception.NotFound()
        self.assertRaises(exc.HTTPBadRequest, self.controller.index, req)

    @mock.patch('karbor.utils.service_is_up')
    @mock.patch('karbor.objects.service.Service.get_by_id')
    def test_service_update_with_admin_context(
            self, mock_get_by_id, mock_service_is_up):
        req = fakes.HTTPRequest.blank('/v1/os-services/1',
                                      use_admin_context=True)
        body = {
            "status": 'disabled',
            'disabled_reason': 'reason'
        }
        mock_service = mock.MagicMock(
            binary='karbor-operationengine', save=mock.MagicMock())
        mock_get_by_id.return_value = mock_service
        mock_service_is_up.return_value = True
        self.controller.update(req, "fake_id", body)
        self.assertTrue(mock_get_by_id.called)
        self.assertTrue(mock_service.save.called)

    def test_service_update_with_non_admin_context(self):
        req = fakes.HTTPRequest.blank('/v1/os-services/1',
                                      use_admin_context=False)
        body = {
            "status": 'disabled',
            'disabled_reason': 'reason'
        }
        self.assertRaises(
            exception.PolicyNotAuthorized,
            self.controller.update,
            req,
            "fake_id",
            body
        )

    @mock.patch('karbor.objects.service.Service.get_by_id')
    def test_update_protection_services(self, mock_get_by_id):
        req = fakes.HTTPRequest.blank('/v1/os-services/1',
                                      use_admin_context=True)
        body = {
            "status": 'disabled',
            'disabled_reason': 'reason'
        }
        mock_service = mock.MagicMock(binary='karbor-protection')
        mock_get_by_id.return_value = mock_service
        self.assertRaises(
            exc.HTTPBadRequest,
            self.controller.update,
            req,
            "fake_id",
            body
        )

    @mock.patch('karbor.objects.service.Service.get_by_id')
    def test_service_update_with_service_not_found(self,
                                                   mock_get_by_id):
        body = {
            "status": 'disabled',
            'disabled_reason': 'reason'
        }
        req = fakes.HTTPRequest.blank('/v1/os-services/1',
                                      use_admin_context=True)
        mock_get_by_id.side_effect = exception.ServiceNotFound
        self.assertRaises(
            exc.HTTPNotFound,
            self.controller.update,
            req,
            "fake_id",
            body
        )

    @mock.patch('karbor.objects.service.Service.get_by_id')
    def test_service_update_with_invalid_disabled_reason(self, mock_get_by_id):
        req = fakes.HTTPRequest.blank('/v1/os-services/1',
                                      use_admin_context=True)
        body = {
            "status": 'enabled',
            'disabled_reason': 'reason'
        }
        mock_service = mock.MagicMock(
            binary='karbor-operationengine', save=mock.MagicMock())
        mock_get_by_id.return_value = mock_service
        self.assertRaises(
            exc.HTTPBadRequest,
            self.controller.update,
            req,
            "fake_id",
            body
        )

    @mock.patch('karbor.utils.service_is_up')
    @mock.patch('karbor.objects.service.Service.get_by_id')
    def test_service_update_with_enabled_status(
            self, mock_get_by_id, mock_service_is_up):
        req = fakes.HTTPRequest.blank('/v1/os-services/1',
                                      use_admin_context=True)
        body = {
            "status": 'enabled'
        }
        mock_service = mock.MagicMock(
            binary='karbor-operationengine', save=mock.MagicMock())
        mock_get_by_id.return_value = mock_service
        mock_service_is_up.return_value = True
        self.controller.update(req, "fake_id", body)
        self.assertTrue(mock_get_by_id.called)
        self.assertTrue(mock_service.save.called)
