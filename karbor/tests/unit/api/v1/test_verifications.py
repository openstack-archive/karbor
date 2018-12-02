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

from karbor.api.v1 import verifications
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF

DEFAULT_PROJECT_ID = '39bb894794b741e982bd26144d2949f6'
DEFAULT_PROVIDER_ID = 'efc6a88b-9096-4bb6-8634-cda182a6e12a'
DEFAULT_CHECKPOINT_ID = '09edcbdc-d1c2-49c1-a212-122627b20968'
DEFAULT_PARAMETERS = {
}


class VerificationApiTest(base.TestCase):
    def setUp(self):
        super(VerificationApiTest, self).setUp()
        self.controller = verifications.VerificationsController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.services.protection.api.API.verification')
    @mock.patch(
        'karbor.objects.verification.Verification.create')
    def test_verification_create(self, mock_verification_create,
                                 mock_rpc_verification):
        verification = self._verification_in_request_body()
        body = {"verification": verification}
        req = fakes.HTTPRequest.blank('/v1/verifications')
        self.controller.create(req, body=body)
        self.assertTrue(mock_verification_create.called)
        self.assertTrue(mock_rpc_verification.called)

    def test_verification_create_InvalidBody(self):
        verification = self._verification_in_request_body()
        body = {"verificationxx": verification}
        req = fakes.HTTPRequest.blank('/v1/verifications')
        self.assertRaises(exception.ValidationError,
                          self.controller.create,
                          req, body=body)

    def test_verification_create_InvalidProviderId(self):
        verification = self._verification_in_request_body(
            provider_id="")
        body = {"verification": verification}
        req = fakes.HTTPRequest.blank('/v1/verifications')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    def test_verification_create_Invalidcheckpoint_id(self):
        verification = self._verification_in_request_body(
            checkpoint_id="")
        body = {"verification": verification}
        req = fakes.HTTPRequest.blank('/v1/verifications')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    @mock.patch(
        'karbor.api.v1.verifications.'
        'VerificationsController._get_all')
    def test_verification_list_detail(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/verifications')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

    @mock.patch(
        'karbor.api.v1.verifications.'
        'VerificationsController._get_all')
    @mock.patch('karbor.api.common.ViewBuilder._get_collection_links')
    def test_verification_list_detail_with_verifications_links(self,
                                                               mock_get_links,
                                                               mock_get_all):
        except_value = [{
            "rel": "next",
            "href": "/v1/verifications?marker"
        }]
        req = fakes.HTTPRequest.blank('/v1/verifications')
        mock_get_links.return_value = except_value
        return_value = self.controller.index(req)
        self.assertTrue(mock_get_all.called)
        self.assertEqual(return_value['verifications_links'], except_value)

    @mock.patch(
        'karbor.api.v1.verifications.'
        'VerificationsController._verification_get')
    def test_verification_show(self, mock_verification_get):
        req = fakes.HTTPRequest.blank('/v1/verifications')
        self.controller.show(
            req, '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')
        self.assertTrue(mock_verification_get.called)

    def test_verification_show_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/verifications/1')
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.show,
            req, "1")

    def _verification_in_request_body(
            self, provider_id=DEFAULT_PROVIDER_ID,
            checkpoint_id=DEFAULT_CHECKPOINT_ID,
            parameters=DEFAULT_PARAMETERS):
        verification_req = {
            'provider_id': provider_id,
            'checkpoint_id': checkpoint_id,
            'parameters': parameters,
        }

        return verification_req
