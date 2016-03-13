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

from smaug.api.v1 import protectables
from smaug import context
from smaug import exception
from smaug.tests import base
from smaug.tests.unit.api import fakes

CONF = cfg.CONF


class ProtectablesApiTest(base.TestCase):
    def setUp(self):
        super(ProtectablesApiTest, self).setUp()
        self.controller = protectables.ProtectablesController()
        self.ctxt = context.RequestContext('admin', 'fakeproject', True)

    @mock.patch(
        'smaug.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_list_detail(self, moak_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        self.controller.index(req)
        self.assertTrue(moak_get_all.called)

    @mock.patch(
        'smaug.services.protection.api.API.show_protectable_type')
    @mock.patch(
        'smaug.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_show(self, moak_get_all, moak_show_protectable_type):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.\
            show(req, 'OS::Keystone::Project')
        self.assertTrue(moak_get_all.called)
        self.assertTrue(moak_show_protectable_type.called)

    @mock.patch(
        'smaug.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_show_Invalid(self, moak_get_all):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.assertRaises(exception.InvalidInput, self.controller.show,
                          req, "1")
        self.assertTrue(moak_get_all.called)

    @mock.patch(
        'smaug.services.protection.api.API.'
        'list_protectable_instances')
    @mock.patch(
        'smaug.api.v1.protectables.ProtectablesController._get_all')
    def test_protectables_instances_show(self, moak_get_all,
                                         list_protectable_instances_type):
        req = fakes.HTTPRequest.blank('/v1/protectables')
        moak_get_all.return_value = ["OS::Keystone::Project"]
        self.controller.\
            instances_index(req, 'OS::Keystone::Project')
        self.assertTrue(moak_get_all.called)
        self.assertTrue(list_protectable_instances_type.called)
