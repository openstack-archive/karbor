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

from karbor.api.v1 import protectables
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF


class ProtectablesApiTest(base.TestCase):
    def setUp(self):
        super(ProtectablesApiTest, self).setUp()
        self.controller = protectables.ProtectablesController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_list_detail(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

    @mock.patch(
        'karbor.services.protection.api.API.show_protectable_type')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_show(
            self, mock_get_all, mock_show_protectable_type):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.show(req, 'OS::Keystone::Project')
        self.assertTrue(mock_get_all.called)
        self.assertTrue(mock_show_protectable_type.called)

    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_show_Invalid(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.assertRaises(exception.InvalidInput, self.controller.show,
                          req, "1")
        self.assertTrue(mock_get_all.called)

    @mock.patch(
        'karbor.services.protection.api.API.'
        'list_protectable_instances')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_index(self, mock_get_all,
                                          mock_list_protectable_instances):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.instances_index(req, 'OS::Keystone::Project')
        self.assertTrue(mock_get_all.called)
        self.assertTrue(mock_list_protectable_instances.called)

    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_index_Invalid(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.assertRaises(exception.InvalidInput,
                          self.controller.instances_index,
                          req, 'abc')

    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_index_InvalidPara(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables?parameters=abc')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.assertRaises(exception.InvalidInput,
                          self.controller.instances_index,
                          req, 'OS::Keystone::Project')

    @mock.patch(
        'karbor.services.protection.api.API.'
        'list_protectable_instances')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_index_InvalidInstance(
            self, mock_get_all,
            mock_list_protectable_instances):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        mock_list_protectable_instances.return_value = [{"name": "abc"}]
        self.assertRaises(exception.InvalidProtectableInstance,
                          self.controller.instances_index,
                          req, 'OS::Keystone::Project')

    @mock.patch(
        'karbor.services.protection.api.API.'
        'list_protectable_dependents')
    @mock.patch(
        'karbor.services.protection.api.API.'
        'show_protectable_instance')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_show(self, mock_get_all,
                                         mock_show_protectable_instance,
                                         mock_list_protectable_dependents):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.instances_show(
            req,
            'OS::Keystone::Project',
            'efc6a88b-9096-4bb6-8634-cda182a6e12a',
        )
        self.assertTrue(mock_get_all.called)
        self.assertTrue(mock_show_protectable_instance.called)
        self.assertTrue(mock_list_protectable_dependents.called)

    def test_protectables_instances_show_InvalidParam(self):
        req = fakes.HTTPRequest.blank('/v1/protectables?parameters=abc')
        self.assertRaises(exception.InvalidInput,
                          self.controller.instances_show,
                          req,
                          'OS::Keystone::Project',
                          'efc6a88b-9096-4bb6-8634-cda182a6e12a')

    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_show_InvalidType(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        self.assertRaises(exception.InvalidInput,
                          self.controller.instances_show,
                          req,
                          'abc',
                          'efc6a88b-9096-4bb6-8634-cda182a6e12a')

    @mock.patch(
        'karbor.services.protection.api.API.'
        'show_protectable_instance')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_show_Invalid(
            self,
            mock_get_all,
            mock_show_protectable_instance):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        mock_get_all.return_value = ["OS::Keystone::Project"]
        mock_show_protectable_instance.side_effect = \
            exception.ProtectableResourceNotFound
        self.assertRaises(exc.HTTPNotFound,
                          self.controller.instances_show,
                          req,
                          'OS::Keystone::Project',
                          'efc6a88b-9096-4bb6-8634-cda182a6e12a')
        mock_show_protectable_instance.side_effect = exception.KarborException
        self.assertRaises(exc.HTTPInternalServerError,
                          self.controller.instances_show,
                          req,
                          'OS::Keystone::Project',
                          'efc6a88b-9096-4bb6-8634-cda182a6e12a')
        mock_show_protectable_instance.return_value = None
        self.assertRaises(exc.HTTPInternalServerError,
                          self.controller.instances_show,
                          req,
                          'OS::Keystone::Project',
                          'efc6a88b-9096-4bb6-8634-cda182a6e12a')
