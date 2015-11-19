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

"""The plans api."""


from oslo_log import log as logging
import webob
from webob import exc

from smaug.api.openstack import wsgi
from smaug.i18n import _LI


LOG = logging.getLogger(__name__)


class PlansController(wsgi.Controller):
    """The Plans API controller for the OpenStack API."""

    def __init__(self):
        super(PlansController, self).__init__()

    def show(self, req, id):
        """Return data about the given plan."""
        context = req.environ['smaug.context']
        LOG.info(_LI("Show plan with id: %s"), id, context=context)
        # TODO(chenying)
        return {'Smaug': "Plans show test."}

    def delete(self, req, id):
        """Delete a plan."""
        context = req.environ['smaug.context']

        LOG.info(_LI("Delete plan with id: %s"), id, context=context)

        # TODO(chenying)
        return webob.Response(status_int=202)

    def index(self, req):
        """Returns a summary list of plans."""

        # TODO(chenying)

        return {'plan': "Plans index test."}

    def detail(self, req):
        """Returns a detailed list of plans."""

        # TODO(chenying)

        return {'plan': "Plans detail test."}

    def create(self, req, body):
        """Creates a new plan."""
        if not self.is_valid_body(body, 'plan'):
            raise exc.HTTPUnprocessableEntity()

        LOG.debug('Create plans request body: %s', body)
        context = req.environ['smaug.context']

        LOG.debug('Create plans request context: %s', context)

        # TODO(chenying)

        return {'plan': "Create a plan test."}

    def update(self, req, id, body):
        """Update a plan."""
        context = req.environ['smaug.context']

        if not body:
            raise exc.HTTPUnprocessableEntity()

        if 'plan' not in body:
            raise exc.HTTPUnprocessableEntity()

        plan = body['plan']

        LOG.info(_LI("Update plan : %s"), plan, context=context)

        return {'plan': "Update a plan test."}


def create_resource():
    return wsgi.Resource(PlansController())
