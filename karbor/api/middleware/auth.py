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
"""
Common Auth Middleware.

"""


import os

from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import request_id
from oslo_serialization import jsonutils
import webob.dec
import webob.exc

from karbor.api.openstack import wsgi
from karbor import context
from karbor.i18n import _
from karbor.wsgi import common as base_wsgi


use_forwarded_for_opt = cfg.BoolOpt(
    'use_forwarded_for',
    default=False,
    help='Treat X-Forwarded-For as the canonical remote address. '
         'Only enable this if you have a sanitizing proxy.')

CONF = cfg.CONF
CONF.register_opt(use_forwarded_for_opt)

LOG = logging.getLogger(__name__)


def pipeline_factory(loader, global_conf, **local_conf):
    """A paste pipeline replica that keys off of auth_strategy."""
    pipeline = local_conf[CONF.auth_strategy]
    pipeline = pipeline.split()
    filters = [loader.get_filter(n) for n in pipeline[:-1]]
    app = loader.get_app(pipeline[-1])
    filters.reverse()
    for filter in filters:
        app = filter(app)
    return app


class InjectContext(base_wsgi.Middleware):
    """Add a 'karbor.context' to WSGI environment."""

    def __init__(self, context, *args, **kwargs):
        self.context = context
        super(InjectContext, self).__init__(*args, **kwargs)

    @webob.dec.wsgify(RequestClass=base_wsgi.Request)
    def __call__(self, req):
        req.environ['karbor.context'] = self.context
        return self.application


class KarborKeystoneContext(base_wsgi.Middleware):
    """Make a request context from keystone headers."""

    @webob.dec.wsgify(RequestClass=base_wsgi.Request)
    def __call__(self, req):
        headers = req.headers
        environ = req.environ

        user_id = headers.get('X_USER_ID') or headers.get('X_USER')
        if user_id is None:
            LOG.debug("Neither X_USER_ID nor X_USER found in request")
            return webob.exc.HTTPUnauthorized()
        # get the roles
        roles = [r.strip() for r in headers.get('X_ROLE', '').split(',')]
        if 'X_TENANT_ID' in headers:
            # This is the new header since Keystone went to ID/Name
            project_id = headers['X_TENANT_ID']
        else:
            # This is for legacy compatibility
            project_id = headers['X_TENANT']

        project_name = headers.get('X_TENANT_NAME')

        req_id = environ.get(request_id.ENV_REQUEST_ID)

        # Get the auth token
        auth_token = headers.get('X_AUTH_TOKEN',
                                 headers.get('X_STORAGE_TOKEN'))

        # Build a context, including the auth_token...
        remote_address = req.remote_addr

        auth_token_info = environ.get('keystone.token_info')

        service_catalog = None
        if headers.get('X_SERVICE_CATALOG') is not None:
            try:
                catalog_header = headers.get('X_SERVICE_CATALOG')
                service_catalog = jsonutils.loads(catalog_header)
            except ValueError:
                raise webob.exc.HTTPInternalServerError(
                    explanation=_('Invalid service catalog json.'))

        if CONF.use_forwarded_for:
            remote_address = headers.get('X-Forwarded-For', remote_address)
        ctx = context.RequestContext(user_id,
                                     project_id,
                                     project_name=project_name,
                                     roles=roles,
                                     auth_token=auth_token,
                                     remote_address=remote_address,
                                     service_catalog=service_catalog,
                                     request_id=req_id,
                                     auth_token_info=auth_token_info)

        environ['karbor.context'] = ctx
        return self.application


class NoAuthMiddleware(base_wsgi.Middleware):
    """Return a fake token if one isn't specified."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        if 'X-Auth-Token' not in req.headers:
            user_id = req.headers.get('X-Auth-User', 'admin')
            project_id = req.headers.get('X-Auth-Project-Id', 'admin')
            os_url = os.path.join(req.url, project_id)
            res = webob.Response()
            # NOTE(vish): This is expecting and returning Auth(1.1), whereas
            #             keystone uses 2.0 auth.  We should probably allow
            #             2.0 auth here as well.
            res.headers['X-Auth-Token'] = '%s:%s' % (user_id, project_id)
            res.headers['X-Server-Management-Url'] = os_url
            res.content_type = 'text/plain'
            res.status = '204'
            return res

        token = req.headers['X-Auth-Token']
        user_id, _sep, project_id = token.partition(':')
        project_id = project_id or user_id
        remote_address = getattr(req, 'remote_address', '127.0.0.1')
        if CONF.use_forwarded_for:
            remote_address = req.headers.get('X-Forwarded-For', remote_address)
        ctx = context.RequestContext(user_id,
                                     project_id,
                                     is_admin=True,
                                     remote_address=remote_address)

        req.environ['karbor.context'] = ctx
        return self.application
