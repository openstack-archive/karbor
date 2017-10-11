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
    def test_protectables_list_detail(self, moak_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        self.controller.index(req)
        self.assertTrue(moak_get_all.called)

    @mock.patch(
        'karbor.services.protection.api.API.show_protectable_type')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_show(
            self, moak_get_all, moak_show_protectable_type):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.show(req, 'OS::Keystone::Project')
        self.assertTrue(moak_get_all.called)
        self.assertTrue(moak_show_protectable_type.called)

    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_show_Invalid(self, moak_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.assertRaises(exception.InvalidInput, self.controller.show,
                          req, "1")
        self.assertTrue(moak_get_all.called)

    @mock.patch(
        'karbor.services.protection.api.API.'
        'list_protectable_instances')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_index(self, moak_get_all,
                                          moak_list_protectable_instances):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.instances_index(req, 'OS::Keystone::Project')
        self.assertTrue(moak_get_all.called)
        self.assertTrue(moak_list_protectable_instances.called)

    @mock.patch(
        'karbor.services.protection.api.API.'
        'list_protectable_dependents')
    @mock.patch(
        'karbor.services.protection.api.API.'
        'show_protectable_instance')
    @mock.patch(
        'karbor.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_show(self, moak_get_all,
                                         moak_show_protectable_instance,
                                         moak_list_protectable_dependents):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.instances_show(
            req,
            'OS::Keystone::Project',
            'efc6a88b-9096-4bb6-8634-cda182a6e12a',
        )
        self.assertTrue(moak_get_all.called)
        self.assertTrue(moak_show_protectable_instance.called)
        self.assertTrue(moak_list_protectable_dependents.called)
