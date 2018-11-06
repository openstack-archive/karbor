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

from oslo_log import log as logging
import six
from six.moves import http_client
import webob.dec
import webob.exc

from karbor.api.openstack import wsgi
from karbor import exception
from karbor import utils
from karbor.wsgi import common as base_wsgi


LOG = logging.getLogger(__name__)


class FaultWrapper(base_wsgi.Middleware):
    """Calls down the middleware stack, making exceptions into faults."""

    _status_to_type = {}

    @staticmethod
    def status_to_type(status):
        if not FaultWrapper._status_to_type:
            for clazz in utils.walk_class_hierarchy(webob.exc.HTTPError):
                FaultWrapper._status_to_type[clazz.code] = clazz
        return FaultWrapper._status_to_type.get(
            status, webob.exc.HTTPInternalServerError)()

    def _error(self, inner, req):
        LOG.error('Middleware error occurred: %s', inner.message)
        safe = getattr(inner, 'safe', False)
        headers = getattr(inner, 'headers', None)
        status = getattr(inner, 'code', http_client.INTERNAL_SERVER_ERROR)
        if status is None:
            status = http_client.INTERNAL_SERVER_ERROR

        msg_dict = dict(url=req.url, status=status)
        LOG.info("%(url)s returned with HTTP %(status)d", msg_dict)
        outer = self.status_to_type(status)
        if headers:
            outer.headers = headers

        if safe:
            msg = (inner.msg if isinstance(inner, exception.KarborException)
                   else six.text_type(inner))
            outer.explanation = msg
        return wsgi.Fault(outer)

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        try:
            return req.get_response(self.application)
        except Exception as ex:
            return self._error(ex, req)
