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
from oslo_utils import excutils
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.api.schemas import plans as plan_schema
from karbor.api import validation
from karbor.common import constants
from karbor.common import notification
from karbor.common.notification import StartNotification
from karbor import exception
from karbor.i18n import _

from karbor import objects
from karbor.objects import base as objects_base
from karbor.policies import plans as plan_policy
from karbor import quota
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
QUOTAS = quota.QUOTAS

LOG = logging.getLogger(__name__)


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
        context.notification = notification.KarborPlanDelete(
            context, request=req)
        try:
            plan = self._plan_get(context, id)
        except exception.PlanNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        context.can(plan_policy.DELETE_POLICY, target_obj=plan)
        project_id = plan.project_id

        try:
            with StartNotification(context, id=id):
                plan.destroy()
        except Exception:
            msg = _("Failed to destroy a plan.")
            raise exc.HTTPServerError(reason=msg)

        try:
            reserve_opts = {'plans': -1}
            reservations = QUOTAS.reserve(context,
                                          project_id=project_id,
                                          **reserve_opts)
        except Exception:
            LOG.exception("Failed to update usages deleting plan.")
        else:
            QUOTAS.commit(context, reservations,
                          project_id=project_id)
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
        context.can(plan_policy.GET_ALL_POLICY)

        if filters is None:
            filters = {}

        all_tenants = utils.get_bool_param('all_tenants', filters)

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

    @validation.schema(plan_schema.create)
    def create(self, req, body):
        """Creates a new plan."""

        LOG.debug('Create plan request body: %s', body)
        context = req.environ['karbor.context']
        context.can(plan_policy.CREATE_POLICY)
        plan = body['plan']
        LOG.debug('Create plan request plan: %s', plan)
        context.notification = notification.KarborPlanCreate(
            context, request=req)

        parameters = plan.get("parameters", None)

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

        try:
            reserve_opts = {'plans': 1}
            reservations = QUOTAS.reserve(context, **reserve_opts)
        except exception.OverQuota as e:
            quota.process_reserve_over_quota(
                context, e,
                resource='plans')
        try:
            plan = objects.Plan(context=context, **plan_properties)
            with StartNotification(
                    context, name=plan.get('name', None)):
                plan.create()
            QUOTAS.commit(context, reservations)
        except Exception:
            with excutils.save_and_reraise_exception():
                try:
                    if plan and 'id' in plan:
                        plan.destroy()
                finally:
                    QUOTAS.rollback(context, reservations)

        retval = self._view_builder.detail(req, plan)

        return retval

    @validation.schema(plan_schema.update)
    def update(self, req, id, body):
        """Update a plan."""
        context = req.environ['karbor.context']
        context.notification = notification.KarborPlanUpdate(
            context, request=req)

        plan = body['plan']
        update_dict = {}

        valid_update_keys = {
            'name',
            'resources',
            'status',
            'description',
        }
        for key in valid_update_keys.intersection(plan):
            update_dict[key] = plan[key]

        if not update_dict:
            msg = _("Missing updated parameters in request body.")
            raise exc.HTTPBadRequest(explanation=msg)

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

        with StartNotification(context, id=id):
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
            context.can(plan_policy.GET_POLICY, target_obj=plan)
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
        context.can(plan_policy.UPDATE_POLICY, target_obj=plan)
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
        try:
            provider = self.protection_api.show_provider(
                context, plan["provider_id"])
        except Exception:
            msg = _("The provider could not be found.")
            raise exc.HTTPBadRequest(explanation=msg)
        options_schema = provider.get(
            "extended_info_schema", {}).get("options_schema", None)
        if options_schema is None:
            msg = _("The option_schema of plugin must be provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        parameters = plan["parameters"]
        if not parameters:
            return
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

            if resource_type not in options_schema:
                LOG.info("Found parameter for an unloaded resource type: %s",
                         resource_type)
                continue

            properties = options_schema[resource_type]["properties"]
            if not set(properties.keys()) >= set(parameter_value.keys()):
                msg = _("The protect property of plan parameters "
                        "is invalid.")
                raise exc.HTTPBadRequest(explanation=msg)


def create_resource():
    return wsgi.Resource(PlansController())
