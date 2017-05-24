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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from webob import exc

import karbor
from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.common import constants
from karbor import exception
from karbor.i18n import _

from karbor import objects
from karbor.objects import base as objects_base
import karbor.policy
from karbor.services.operationengine import api as operationengine_api
from karbor.services.protection import api as protection_api
from karbor import utils

import six

query_plan_filters_opt = cfg.ListOpt('query_plan_filters',
                                     default=['name', 'status',
                                              'description'],
                                     help="Plan filter options which "
                                          "non-admin user could use to "
                                          "query plans. Default values "
                                          "are: ['name', 'status', "
                                          "'description']")
CONF = cfg.CONF
CONF.register_opt(query_plan_filters_opt)

LOG = logging.getLogger(__name__)


def check_policy(context, action, target_obj=None):
    target = {
        'project_id': context.project_id,
        'user_id': context.user_id,
    }

    if isinstance(target_obj, objects_base.KarborObject):
        # Turn object into dict so target.update can work
        target.update(
            target_obj.obj_to_primitive() or {})
    else:
        target.update(target_obj or {})

    _action = 'plan:%s' % action
    karbor.policy.enforce(context, _action, target)


class PlanViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "plans"

    def detail(self, request, plan):
        """Detailed view of a single plan."""

        resources = plan.get('resources')
        resources_list = []
        for resource in resources:
            resource_dict = {}
            resource_dict['id'] = resource.pop('id')
            resource_dict['name'] = resource.pop('name')
            resource_dict['type'] = resource.pop('type')
            extra_info = resource.pop('extra_info', None)
            if extra_info:
                resource_dict['extra_info'] = jsonutils.loads(
                    extra_info)
            resources_list.append(resource_dict)
        plan_ref = {
            'plan': {
                'id': plan.get('id'),
                'name': plan.get('name'),
                'description': plan.get('description'),
                'resources': resources_list,
                'provider_id': plan.get('provider_id'),
                'status': plan.get('status'),
                'parameters': plan.get('parameters'),
            }
        }
        return plan_ref

    def detail_list(self, request, plans, plan_count=None):
        """Detailed view of a list of plans."""
        return self._list_view(self.detail, request, plans,
                               plan_count,
                               self._collection_name)

    def _list_view(self, func, request, plans, plan_count,
                   coll_name=_collection_name):
        """Provide a view for a list of plans.

        :param func: Function used to format the plan data
        :param request: API request
        :param plans: List of plans in dictionary format
        :param plan_count: Length of the original list of plans
        :param coll_name: Name of collection, used to generate the next link
                          for a pagination query
        :returns: Plan data in dictionary format
        """
        plans_list = [func(request, plan)['plan'] for plan in plans]
        plans_links = self._get_collection_links(request,
                                                 plans,
                                                 coll_name,
                                                 plan_count)
        plans_dict = {}
        plans_dict['plans'] = plans_list
        if plans_links:
            plans_dict['plans_links'] = plans_links

        return plans_dict


class PlansController(wsgi.Controller):
    """The Plans API controller for the OpenStack API."""

    _view_builder_class = PlanViewBuilder

    def __init__(self):
        self.operationengine_api = operationengine_api.API()
        self.protection_api = protection_api.API()
        super(PlansController, self).__init__()

    def show(self, req, id):
        """Return data about the given plan."""
        context = req.environ['karbor.context']

        LOG.info("Show plan with id: %s", id, context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid plan id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            plan = self._plan_get(context, id)
        except exception.PlanNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show plan request issued successfully.",
                 resource={'id': plan.id})
        return self._view_builder.detail(req, plan)

    def delete(self, req, id):
        """Delete a plan."""
        context = req.environ['karbor.context']

        LOG.info("Delete plan with id: %s", id, context=context)

        try:
            plan = self._plan_get(context, id)
        except exception.PlanNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        check_policy(context, 'delete', plan)
        plan.destroy()
        LOG.info("Delete plan request issued successfully.",
                 resource={'id': plan.id})

    def index(self, req):
        """Returns a list of plans, transformed through view builder."""
        context = req.environ['karbor.context']

        LOG.info("Show plan list", context=context)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        utils.remove_invalid_filter_options(context,
                                            filters,
                                            self._get_plan_filter_options())

        utils.check_filters(filters)
        plans = self._get_all(context, marker, limit,
                              sort_keys=sort_keys,
                              sort_dirs=sort_dirs,
                              filters=filters,
                              offset=offset)

        retval_plans = self._view_builder.detail_list(req, plans)

        LOG.info("Show plan list request issued successfully.")

        return retval_plans

    def _get_all(self, context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
        check_policy(context, 'get_all')

        if filters is None:
            filters = {}

        all_tenants = utils.get_bool_param('all_tenants', filters)

        try:
            if limit is not None:
                limit = int(limit)
                if limit < 0:
                    msg = _('limit param must be positive')
                    raise exception.InvalidInput(reason=msg)
        except ValueError:
            msg = _('limit param must be an integer')
            raise exception.InvalidInput(reason=msg)

        if filters:
            LOG.debug("Searching by: %s.", six.text_type(filters))

        if context.is_admin and all_tenants:
            # Need to remove all_tenants to pass the filtering below.
            del filters['all_tenants']
            plans = objects.PlanList.get_all(context, marker, limit,
                                             sort_keys=sort_keys,
                                             sort_dirs=sort_dirs,
                                             filters=filters,
                                             offset=offset)
        else:
            plans = objects.PlanList.get_all_by_project(
                context, context.project_id, marker, limit,
                sort_keys=sort_keys, sort_dirs=sort_dirs, filters=filters,
                offset=offset)

        LOG.info("Get all plans completed successfully.")
        return plans

    def _get_plan_filter_options(self):
        """Return plan search options allowed by non-admin."""
        return CONF.query_plan_filters

    def create(self, req, body):
        """Creates a new plan."""
        if not self.is_valid_body(body, 'plan'):
            raise exc.HTTPUnprocessableEntity()

        LOG.debug('Create plan request body: %s', body)
        context = req.environ['karbor.context']
        check_policy(context, 'create')
        plan = body['plan']
        LOG.debug('Create plan request plan: %s', plan)

        if not plan.get("provider_id"):
            msg = _("provider_id must be provided when creating "
                    "a plan.")
            raise exception.InvalidInput(reason=msg)

        parameters = plan.get("parameters", None)

        if parameters is None:
            msg = _("parameters must be provided when creating "
                    "a plan.")
            raise exception.InvalidInput(reason=msg)

        if not isinstance(parameters, dict):
            msg = _("parameters must be a dict when creating a plan.")
            raise exception.InvalidInput(reason=msg)

        self.validate_name_and_description(plan)
        self.validate_plan_resources(plan)
        self.validate_plan_parameters(context, plan)

        resources = plan.get('resources', None)
        if resources:
            for resource in resources:
                extra_info = resource.get('extra_info', None)
                if extra_info is not None:
                    resource['extra_info'] = jsonutils.dumps(extra_info)

        plan_properties = {
            'name': plan.get('name', None),
            'description': plan.get('description', None),
            'provider_id': plan.get('provider_id', None),
            'project_id': context.project_id,
            'status': constants.PLAN_STATUS_SUSPENDED,
            'resources': resources,
            'parameters': parameters,
        }

        plan = objects.Plan(context=context, **plan_properties)
        plan.create()

        retval = self._view_builder.detail(req, plan)

        return retval

    def update(self, req, id, body):
        """Update a plan."""
        context = req.environ['karbor.context']

        if not body:
            msg = _("Missing request body")
            raise exc.HTTPBadRequest(explanation=msg)

        if 'plan' not in body:
            msg = _("Missing required element '%s' in request body") % 'plan'
            raise exc.HTTPBadRequest(explanation=msg)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid plan id provided.")
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

        resources = update_dict.get('resources', None)
        if resources:
            for resource in resources:
                extra_info = resource.get('extra_info', None)
                if extra_info is not None:
                    resource['extra_info'] = jsonutils.dumps(extra_info)

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
        if not uuidutils.is_uuid_like(plan_id):
            msg = _("Invalid plan id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        plan = objects.Plan.get_by_id(context, plan_id)
        try:
            check_policy(context, 'get', plan)
        except exception.PolicyNotAuthorized:
            # raise PlanNotFound instead to make sure karbor behaves
            # as it used to
            raise exception.PlanNotFound(plan_id=plan_id)
        LOG.info("Plan info retrieved successfully.", resource=plan)
        return plan

    def _plan_update(self, context, plan, fields):
        if plan['status'] != constants.PLAN_STATUS_SUSPENDED:
            LOG.info("Unable to update plan, because it is in %s state.",
                     plan['status'])
            msg = _("The plan can be only updated in suspended status.")
            raise exception.InvalidPlan(reason=msg)
        # TODO(chenying) replication scene: need call rpc API when
        # the status of the plan is changed.
        if isinstance(plan, objects_base.KarborObject):
            plan.update(fields)
            plan.save()
            LOG.info("Plan updated successfully.", resource=plan)
        else:
            msg = _("The parameter plan must be a object of "
                    "KarborObject class.")
            raise exception.InvalidInput(reason=msg)

    def validate_plan_resources(self, plan):
        resources_list = plan["resources"]
        if (isinstance(resources_list, list)) and (len(resources_list) > 0):
            for resource in resources_list:
                if (isinstance(resource, dict) and (len(resource) >= 3) and
                        {"id", "type", 'name'}.issubset(resource)):
                    pass
                else:
                    msg = _("Resource in list must be a dict when creating a "
                            "plan.The keys of resource are id,type and name.")
                    raise exception.InvalidInput(reason=msg)
        else:
            msg = _("list resources must be provided when creating "
                    "a plan.")
            raise exception.InvalidInput(reason=msg)

    def validate_plan_parameters(self, context, plan):
        parameters = plan["parameters"]
        if not parameters:
            return
        try:
            provider = self.protection_api.show_provider(
                context, plan["provider_id"])
        except exception:
            msg = _("The provider could not be found.")
            raise exc.HTTPBadRequest(explanation=msg)
        options_schema = provider.get(
            "extended_info_schema", {}).get("options_schema", None)
        if options_schema is None:
            msg = _("The option_schema of plugin must be provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        for resource_key, parameter_value in parameters.items():
            if "#" in resource_key:
                resource_type, resource_id = resource_key.split("#")
                if not uuidutils.is_uuid_like(resource_id):
                    msg = _("The resource_id must be a uuid.")
                    raise exc.HTTPBadRequest(explanation=msg)
            else:
                resource_type = resource_key
            if resource_type not in constants.RESOURCE_TYPES:
                msg = _("The key of plan parameters is invalid.")
                raise exc.HTTPBadRequest(explanation=msg)
            properties = options_schema[resource_type]["properties"]
            if not set(properties.keys()) > set(parameter_value.keys()):
                msg = _("The protect property of plan parameters "
                        "is invalid.")
                raise exc.HTTPBadRequest(explanation=msg)


def create_resource():
    return wsgi.Resource(PlansController())
