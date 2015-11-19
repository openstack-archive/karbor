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

from smaug.api.openstack import ProjectMapper
from smaug.api.v1 import router
from smaug.tests import base
from smaug.tests.unit.api import fakes


class PlansRouterTestCase(base.TestCase):
    def setUp(self):
        super(PlansRouterTestCase, self).setUp()
        mapper = ProjectMapper()
        self.app = router.APIRouter(mapper)

    def test_plans(self):
        req = fakes.HTTPRequest.blank('/fakeproject/plans')
        req.method = 'GET'
        req.content_type = 'application/json'
        response = req.get_response(self.app)
        self.assertEqual(200, response.status_int)

    def test_plans_detail(self):
        req = fakes.HTTPRequest.blank('/fakeproject/plans/detail')
        req.method = 'GET'
        req.content_type = 'application/json'
        response = req.get_response(self.app)
        self.assertEqual(200, response.status_int)
