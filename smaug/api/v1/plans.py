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

import smaug
from smaug.api.openstack import wsgi
from smaug import exception
from smaug.i18n import _, _LI
from smaug import objects
from smaug.objects import base as objects_base
from smaug.operationengine import api as operationengine_api
import smaug.policy

LOG = logging.getLogger(__name__)


def check_policy(context, action, target_obj=None):
    target = {
        'project_id': context.project_id,
        'user_id': context.user_id,
    }

    if isinstance(target_obj, objects_base.SmaugObject):
        # Turn object into dict so target.update can work
        target.update(
            target_obj.obj_to_primitive() or {})
    else:
        target.update(target_obj or {})

    _action = 'plan:%s' % action
    smaug.policy.enforce(context, _action, target)


class PlanViewBuilder(object):
    """Model a server API response as a python dictionary."""

    _collection_name = "plans"

    def __init__(self):
        """Initialize view builder."""
        super(PlanViewBuilder, self).__init__()

    def detail(self, request, plan):
        """Detailed view of a single plan."""
        plan_ref = {
            'plan': {
                'id': plan.get('id'),
                'name': plan.get('name'),
                'resources': plan.get('resources'),
                'provider_id': plan.get('provider_id'),
                'status': plan.get('status'),
            }
        }
        return plan_ref


class PlansController(wsgi.Controller):
    """The Plans API controller for the OpenStack API."""

    _view_builder_class = PlanViewBuilder

    def __init__(self):
        self.operationengine_api = operationengine_api.API()
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

        LOG.debug('Create plan request body: %s', body)
        context = req.environ['smaug.context']
        check_policy(context, 'create')
        plan = body['plan']
        LOG.debug('Create plan request plan: %s', plan)

        if not plan.get("provider_id"):
            msg = _("provider_id must be provided when creating "
                    "a plan.")
            raise exception.InvalidInput(reason=msg)

        self.validate_name_and_description(plan)
        self.validate_plan_resources(plan)

        plan_properties = {
            'name': plan.get('name', None),
            'provider_id': plan.get('provider_id', None),
            'project_id': context.project_id,
            'status': 'suspended',
            'resources': plan.get('resources', None),
        }

        plan = objects.Plan(context=context, **plan_properties)
        plan.create()

        retval = self._view_builder.detail(req, plan)

        return retval

    def update(self, req, id, body):
        """Update a plan."""
        context = req.environ['smaug.context']

        if not body:
            msg = _("Missing request body")
            raise exc.HTTPBadRequest(explanation=msg)

        if 'plan' not in body:
            msg = _("Missing required element '%s' in request body") % 'plan'
            raise exc.HTTPBadRequest(explanation=msg)

        plan = body['plan']
        update_dict = {}

        valid_update_keys = {
            'name',
            'resources',
            'status',
        }
        for key in valid_update_keys.intersection(plan):
            update_dict[key] = plan[key]

        if update_dict is None:
            msg = _("Missing updated parameters in request body.")
            raise exc.HTTPBadRequest(explanation=msg)

        self.validate_name_and_description(update_dict)
        if update_dict.get("resources"):
            self.validate_plan_resources(update_dict)

        try:
            plan = self._plan_get(context, id)
        except exception.PlanNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        check_policy(context, 'update', plan)
        self._plan_update(context, plan, update_dict)

        plan.update(update_dict)

        retval = self._view_builder.detail(req, plan)
        return retval

    def _plan_get(self, context, plan_id):
        plan = objects.Plan.get_by_id(context, plan_id)
        try:
            check_policy(context, 'get', plan)
        except exception.PolicyNotAuthorized:
            # raise PlanNotFound instead to make sure smaug behaves
            # as it used to
            raise exception.PlanNotFound(plan_id=plan_id)
        LOG.info(_LI("Plan info retrieved successfully."), resource=plan)
        return plan

    def _plan_update(self, context, plan, fields):
        if plan['status'] != 'suspended':
            LOG.info(_LI("Unable to update plan, "
                         "because it is in %s state."), plan['status'])
            msg = _("The plan can be only updated in suspended status.")
            raise exception.InvalidPlan(reason=msg)
        # TODO(chenying) replication scene: need call rpc API when
        # the status of the plan is changed.
        if isinstance(plan, objects_base.SmaugObject):
            plan.update(fields)
            plan.save()
            LOG.info(_LI("Plan updated successfully."), resource=plan)
        else:
            msg = _("The parameter plan must be a object of "
                    "SmaugObject class.")
            raise exception.InvalidInput(reason=msg)

    def validate_plan_resources(self, plan):
        resources_list = plan["resources"]
        if (isinstance(resources_list, list)) and (len(resources_list) > 0):
            for resource in resources_list:
                if (isinstance(resource, dict) and (len(resource) == 2) and
                        {"id", "type"}.issubset(resource)):
                    pass
                else:
                    msg = _("Resource in list must be a dict when creating"
                            " a plan.The keys of resource are id and type.")
                    raise exception.InvalidInput(reason=msg)
        else:
            msg = _("list resources must be provided when creating "
                    "a plan.")
            raise exception.InvalidInput(reason=msg)


def create_resource():
    return wsgi.Resource(PlansController())
