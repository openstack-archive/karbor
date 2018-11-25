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

"""The copy api."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.api.schemas import copies as copy_schema
from karbor.api import validation
from karbor import exception
from karbor.i18n import _

from karbor import objects
from karbor.policies import copies as copy_policy
from karbor.services.protection import api as protection_api

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class CopiesViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    def detail(self, request, copy):
        """Detailed view of a single copy."""
        copy_ref = {
            'copy': {
                'project_id': copy.get('project_id'),
                'provider_id': copy.get('provider_id'),
                'plan_id': copy.get('plan_id'),
                'checkpoint_id': copy.get('checkpoint_id'),
                'parameters': copy.get('parameters'),
            }
        }
        return copy_ref


class CopiesController(wsgi.Controller):
    """The copy API controller for the OpenStack API."""

    _view_builder_class = CopiesViewBuilder

    def __init__(self):
        self.protection_api = protection_api.API()
        super(CopiesController, self).__init__()

    @validation.schema(copy_schema.create)
    def create(self, req, provider_id, body):
        """Creates a new copy."""

        LOG.debug('Create copy request body: %s', body)
        context = req.environ['karbor.context']
        context.can(copy_policy.CREATE_POLICY)
        copy = body['copy']
        plan_id = copy.get("plan_id", None)

        if not uuidutils.is_uuid_like(provider_id):
            msg = _("Invalid provider id provided.")
            raise exception.InvalidInput(reason=msg)

        parameters = copy.get("parameters", None)

        try:
            plan = objects.Plan.get_by_id(context, plan_id)
        except exception.PlanNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        if provider_id != plan.provider_id:
            msg = _("The provider id is not the same as the value "
                    "in the plan.")
            raise exception.InvalidInput(reason=msg)

        filters = {'plan_id': plan_id}
        checkpoints = self.protection_api.list_checkpoints(
            context, provider_id, marker=None, limit=None,
            sort_keys=None, sort_dirs=None, filters=filters, offset=None,
            all_tenants=False)

        if not checkpoints:
            msg = _("The plan has not been protected.")
            raise exception.InvalidInput(reason=msg)

        plan.parameters.update(parameters)
        try:
            checkpoint_copy = self.protection_api.copy(context, plan)
        except Exception:
            LOG.exception("Failed to create checkpoint copies.")
            raise

        copy = {
            'project_id': context.project_id,
            'provider_id': plan.provider_id,
            'plan_id': plan.id,
            'checkpoint_id': checkpoint_copy,
            'parameters': parameters
        }

        retval = self._view_builder.detail(req, copy)
        return retval


def create_resource():
    return wsgi.Resource(CopiesController())
