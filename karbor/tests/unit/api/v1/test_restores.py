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

from karbor.api.v1 import restores
from karbor import context
from karbor import exception
from karbor.tests import base
from karbor.tests.unit.api import fakes

CONF = cfg.CONF

DEFAULT_PROVIDER_ID = 'efc6a88b-9096-4bb6-8634-cda182a6e12a'
DEFAULT_CHECKPOINT_ID = '09edcbdc-d1c2-49c1-a212-122627b20968'
DEFAULT_RESTORE_TARGET = '192.168.1.2/identity/'
DEFAULT_RESTORE_AUTH = {
    'type': 'password',
    'username': 'demo',
    'password': 'test',
}
DEFAULT_PARAMETERS = {
}


class RestoreApiTest(base.TestCase):
    def setUp(self):
        super(RestoreApiTest, self).setUp()
        self.controller = restores.RestoresController()
        self.ctxt = context.RequestContext('demo', 'fakeproject', True)

    @mock.patch(
        'karbor.services.protection.api.API.restore')
    @mock.patch(
        'karbor.objects.restore.Restore.create')
    def test_restore_create(self, mock_restore_create,
                            mock_rpc_restore):
        restore = self._restore_in_request_body()
        body = {"restore": restore}
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.controller.create(req, body=body)
        self.assertTrue(mock_restore_create.called)
        self.assertTrue(mock_rpc_restore.called)

    def test_restore_create_InvalidBody(self):
        restore = self._restore_in_request_body()
        body = {"restorexx": restore}
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    def test_restore_create_InvalidProviderId(self):
        restore = self._restore_in_request_body(provider_id="")
        body = {"restore": restore}
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    def test_restore_create_Invalidcheckpoint_id(self):
        restore = self._restore_in_request_body(checkpoint_id="")
        body = {"restore": restore}
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.assertRaises(exception.ValidationError, self.controller.create,
                          req, body=body)

    @mock.patch('karbor.services.protection.api.API.restore')
    def test_restore_create_with_checkpoint_not_allowed_exception(
            self, mock_restore):
        mock_restore.side_effect = exception.AccessCheckpointNotAllowed
        restore = self._restore_in_request_body()
        body = {"restore": restore}
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.assertRaises(exc.HTTPForbidden, self.controller.create,
                          req, body=body)

    @mock.patch(
        'karbor.api.v1.restores.RestoresController._get_all')
    def test_restore_list_detail(self, mock_get_all):
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

    @mock.patch(
        'karbor.api.v1.restores.RestoresController._get_all')
    def test_restore_index_limit_offset(self, mock_get_all):
        req = fakes.HTTPRequest.blank(
            '/v1/restores?limit=2&offset=1')
        self.controller.index(req)
        self.assertTrue(mock_get_all.called)

        req = fakes.HTTPRequest.blank('/v1/restores?limit=-1&offset=1')
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

        req = fakes.HTTPRequest.blank('/v1/restores?limit=a&offset=1')
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

        url = '/v1/restores?limit=2&offset=43543564546567575'
        req = fakes.HTTPRequest.blank(url)
        self.assertRaises(exc.HTTPBadRequest,
                          self.controller.index,
                          req)

    @mock.patch(
        'karbor.api.v1.restores.RestoresController.'
        '_restore_get')
    def test_restore_show(self, mock_restore_get):
        req = fakes.HTTPRequest.blank('/v1/restores')
        self.controller.show(
            req, '2a9ce1f3-cc1a-4516-9435-0ebb13caa398')
        self.assertTrue(mock_restore_get.called)

    def test_restore_show_Invalid(self):
        req = fakes.HTTPRequest.blank('/v1/restores/1')
        self.assertRaises(
            exc.HTTPBadRequest, self.controller.show,
            req, "1")

    def _restore_in_request_body(
            self, provider_id=DEFAULT_PROVIDER_ID,
            checkpoint_id=DEFAULT_CHECKPOINT_ID,
            restore_target=DEFAULT_RESTORE_TARGET,
            restore_auth=DEFAULT_RESTORE_AUTH,
            parameters=DEFAULT_PARAMETERS):
        restore_req = {
            'provider_id': provider_id,
            'checkpoint_id': checkpoint_id,
            'restore_target': restore_target,
            'restore_auth': restore_auth,
            'parameters': parameters,
        }

        return restore_req
