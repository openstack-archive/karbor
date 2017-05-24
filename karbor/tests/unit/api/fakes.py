# Copyright 2010 OpenStack Foundation
# All Rights Reserved.
#
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

from oslo_service import wsgi
from oslo_utils import uuidutils

import routes
import webob
import webob.dec
import webob.request

from karbor.api.openstack import wsgi as os_wsgi
from karbor import context
from karbor.services.protection.protection_plugins.volume \
    import volume_plugin_cinder_schemas as cinder_schemas

FAKE_UUID = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
FAKE_UUIDS = {}
PROVIDER_OS = {
    "description": "This provider uses OpenStack's own services "
                   "(swift, cinder) as storage",
    "extended_info_schema": {
        "options_schema": {
            "OS::Cinder::Volume": cinder_schemas.OPTIONS_SCHEMA
        },
        "saved_info_schema": {
            "OS::Cinder::Volume": cinder_schemas.SAVED_INFO_SCHEMA
        },
        "restore_schema": {
            "OS::Cinder::Volume": cinder_schemas.RESTORE_SCHEMA
        }
    },
    "id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
    "name": "OS Infra Provider"
}


class Context(object):
    pass


class FakeRouter(wsgi.Router):
    def __init__(self, ext_mgr=None):
        pass

    @webob.dec.wsgify
    def __call__(self, req):
        res = webob.Response()
        res.status = '200'
        res.headers['X-Test-Success'] = 'True'
        return res


@webob.dec.wsgify
def fake_wsgi(self, req):
    return self.application


class FakeToken(object):
    id_count = 0

    def __getitem__(self, key):
        return getattr(self, key)

    def __init__(self, **kwargs):
        FakeToken.id_count += 1
        self.id = FakeToken.id_count
        for k, v in kwargs.items():
            setattr(self, k, v)


class FakeRequestContext(context.RequestContext):
    def __init__(self, *args, **kwargs):
        kwargs['auth_token'] = kwargs.get('auth_token', 'fake_auth_token')
        super(FakeRequestContext, self).__init__(*args, **kwargs)


class HTTPRequest(webob.Request):

    @classmethod
    def blank(cls, *args, **kwargs):
        if args is not None:
            if args[0].find('v1') == 0:
                kwargs['base_url'] = 'http://localhost/v1'
            else:
                kwargs['base_url'] = 'http://localhost/v2'

        use_admin_context = kwargs.pop('use_admin_context', False)
        out = os_wsgi.Request.blank(*args, **kwargs)
        out.environ['karbor.context'] = FakeRequestContext(
            'fake_user',
            'fakeproject',
            is_admin=use_admin_context)
        return out


class TestRouter(wsgi.Router):
    def __init__(self, controller):
        mapper = routes.Mapper()
        mapper.resource("test", "tests",
                        controller=os_wsgi.Resource(controller))
        super(TestRouter, self).__init__(mapper)


def get_fake_uuid(token=0):
    if token not in FAKE_UUIDS:
        FAKE_UUIDS[token] = uuidutils.generate_uuid()
    return FAKE_UUIDS[token]
