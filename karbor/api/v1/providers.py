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

"""The providers api."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.common import constants
from karbor import exception
from karbor.i18n import _

from karbor import objects
import karbor.policy
from karbor.services.protection import api as protection_api
from karbor import utils

import six

query_provider_filters_opts = [
    cfg.ListOpt(
        'query_provider_filters',
        default=['name', 'description'],
        help=(
            "Provider filter options which non-admin user could use to "
            "query providers. Default values are: ['name', 'description']"
        )
    ),
]

query_checkpoint_filters_opts = [
    cfg.ListOpt(
        'query_checkpoint_filters',
        default=['project_id', 'plan_id', 'start_date', 'end_date'],
        help=(
            "Checkpoint filter options which non-admin user could use to "
            "query checkpoints. Default values are: ['project_id', "
            "'plan_id', 'start_date', 'end_date']"
        )
    ),
]

CONF = cfg.CONF
CONF.register_opts(query_provider_filters_opts)
CONF.register_opts(query_checkpoint_filters_opts)

LOG = logging.getLogger(__name__)


def check_policy(context, action):
    target = {
        'project_id': context.project_id,
        'user_id': context.user_id,
    }
    _action = 'provider:%s' % action
    karbor.policy.enforce(context, _action, target)


class ProviderViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "providers"

    def detail(self, request, provider):
        """Detailed view of a single provider."""
        provider_ref = {
            'provider': {
                'id': provider.get('id'),
                'name': provider.get('name'),
                'description': provider.get('description'),
                'extended_info_schema': provider.get('extended_info_schema'),
            }
        }
        return provider_ref

    def detail_list(self, request, providers, provider_count=None):
        """Detailed view of a list of providers."""
        return self._list_view(self.detail, request, providers,
                               provider_count,
                               self._collection_name)

    def _list_view(self, func, request, providers, provider_count,
                   coll_name=_collection_name):
        """Provide a view for a list of provider.

        :param func: Function used to format the provider data
        :param request: API request
        :param providers: List of providers in dictionary format
        :param provider_count: Length of the original list of providers
        :param coll_name: Name of collection, used to generate the next link
                          for a pagination query
        :returns: Provider data in dictionary format
        """
        providers_list = [func(request, provider)['provider']
                          for provider in providers]
        providers_links = self._get_collection_links(request,
                                                     providers,
                                                     coll_name,
                                                     provider_count)
        providers_dict = {
            "providers": providers_list
        }
        if providers_links:
            providers_dict['providers_links'] = providers_links

        return providers_dict


class CheckpointViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "checkpoints"

    def detail(self, request, checkpoint):
        """Detailed view of a single checkpoint."""
        checkpoint_ref = {
            'checkpoint': {
                'id': checkpoint.get('id'),
                'project_id': checkpoint.get('project_id'),
                'status': checkpoint.get('status'),
                'protection_plan': checkpoint.get('protection_plan'),
                'resource_graph': checkpoint.get('resource_graph'),
                'created_at': checkpoint.get('created_at'),
                'extra_info': checkpoint.get('extra_info'),
            }
        }
        return checkpoint_ref

    def detail_list(self, request, checkpoints, checkpoint_count=None):
        """Detailed view of a list of checkpoints."""
        return self._list_view(self.detail, request, checkpoints,
                               checkpoint_count,
                               self._collection_name)

    def _list_view(self, func, request, checkpoints, checkpoint_count,
                   coll_name=_collection_name):
        """Provide a view for a list of checkpoint.

        :param func: Function used to format the checkpoint data
        :param request: API request
        :param checkpoints: List of checkpoints in dictionary format
        :param checkpoint_count: Length of the original list of checkpoints
        :param coll_name: Name of collection, used to generate the next link
                          for a pagination query
        :returns: Checkpoint data in dictionary format
        """
        checkpoints_list = [func(request, checkpoint)['checkpoint']
                            for checkpoint in checkpoints]
        checkpoints_links = self._get_collection_links(request,
                                                       checkpoints,
                                                       coll_name,
                                                       checkpoint_count)
        checkpoints_dict = {
            "checkpoints": checkpoints_list
        }
        if checkpoints_links:
            checkpoints_dict['checkpoints_links'] = checkpoints_links

        return checkpoints_dict


class ProvidersController(wsgi.Controller):
    """The Providers API controller for the OpenStack API."""

    _view_builder_class = ProviderViewBuilder

    def __init__(self):
        self.protection_api = protection_api.API()
        self._checkpoint_view_builder = CheckpointViewBuilder()
        super(ProvidersController, self).__init__()

    def show(self, req, id):
        """Return data about the given provider id."""
        context = req.environ['karbor.context']

        LOG.info("Show provider with id: %s", id)

        try:
            provider = self._provider_get(context, id)
        except exception.ProviderNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show provider request issued successfully.",
                 resource={'id': provider.get("id")})
        return self._view_builder.detail(req, provider)

    def index(self, req):
        """Returns a list of providers, transformed through view builder."""
        context = req.environ['karbor.context']

        LOG.info("Show provider list", context=context)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        utils.remove_invalid_filter_options(
            context,
            filters,
            self._get_provider_filter_options())

        utils.check_filters(filters)
        providers = self._get_all(context, marker, limit,
                                  sort_keys=sort_keys,
                                  sort_dirs=sort_dirs,
                                  filters=filters,
                                  offset=offset)

        retval_providers = self._view_builder.detail_list(req, providers)

        LOG.info("Show provider list request issued successfully.")

        return retval_providers

    def _get_all(self, context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
        check_policy(context, 'get_all')

        if filters is None:
            filters = {}

        try:
            if limit is not None:
                limit = int(limit)
                if limit <= 0:
                    msg = _('limit param must be positive')
                    raise exception.InvalidInput(reason=msg)
        except ValueError:
            msg = _('limit param must be an integer')
            raise exception.InvalidInput(reason=msg)

        if filters:
            LOG.debug("Searching by: %s.", six.text_type(filters))

        providers = self.protection_api.list_providers(
            context, marker, limit,
            sort_keys=sort_keys,
            sort_dirs=sort_dirs,
            filters=filters,
            offset=offset)

        LOG.info("Get all providers completed successfully.")
        return providers

    def _get_provider_filter_options(self):
        """Return provider search options allowed by non-admin."""
        return CONF.query_provider_filters

    def _get_checkpoint_filter_options(self):
        """Return checkpoint search options allowed by non-admin."""
        return CONF.query_checkpoint_filters

    def _provider_get(self, context, provider_id):
        if not uuidutils.is_uuid_like(provider_id):
            msg = _("Invalid provider id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            check_policy(context, 'get')
        except exception.PolicyNotAuthorized:
            # raise ProviderNotFound instead to make sure karbor behaves
            # as it used to
            raise exception.ProviderNotFound(provider_id=provider_id)

        provider = self.protection_api.show_provider(context, provider_id)

        LOG.info("Provider info retrieved successfully.")
        return provider

    def checkpoints_index(self, req, provider_id):
        """Returns a list of checkpoints, transformed through view builder."""
        context = req.environ['karbor.context']

        LOG.info("Show checkpoints list. provider_id:%s", provider_id)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        utils.remove_invalid_filter_options(
            context,
            filters,
            self._get_checkpoint_filter_options())

        utils.check_filters(filters)
        checkpoints = self._checkpoints_get_all(
            context, provider_id, marker, limit,
            sort_keys=sort_keys, sort_dirs=sort_dirs,
            filters=filters, offset=offset)

        retval_checkpoints = self._checkpoint_view_builder.detail_list(
            req, checkpoints)

        LOG.info("Show checkpoints list request issued successfully.")
        return retval_checkpoints

    def _checkpoints_get_all(self, context, provider_id, marker=None,
                             limit=None, sort_keys=None, sort_dirs=None,
                             filters=None, offset=None):
        check_policy(context, 'checkpoint_get_all')

        if filters is None:
            filters = {}

        try:
            if limit is not None:
                limit = int(limit)
                if limit <= 0:
                    msg = _('limit param must be positive')
                    raise exception.InvalidInput(reason=msg)
        except ValueError:
            msg = _('limit param must be an integer')
            raise exception.InvalidInput(reason=msg)

        if filters:
            LOG.debug("Searching by: %s.", six.text_type(filters))

        checkpoints = self.protection_api.list_checkpoints(
            context, provider_id, marker, limit,
            sort_keys=sort_keys,
            sort_dirs=sort_dirs,
            filters=filters,
            offset=offset)

        LOG.info("Get all checkpoints completed successfully.")
        return checkpoints

    def checkpoints_create(self, req, provider_id, body):
        """Creates a new checkpoint."""
        if not self.is_valid_body(body, 'checkpoint'):
            raise exc.HTTPUnprocessableEntity()

        context = req.environ['karbor.context']

        LOG.debug('Create checkpoint request '
                  'body: %s provider_id:%s', body, provider_id)

        check_policy(context, 'checkpoint_create')
        checkpoint = body['checkpoint']
        LOG.debug('Create checkpoint request checkpoint: %s',
                  checkpoint)

        if not provider_id:
            msg = _("provider_id must be provided when creating "
                    "a checkpoint.")
            raise exception.InvalidInput(reason=msg)

        plan_id = checkpoint.get("plan_id")

        if not plan_id:
            msg = _("plan_id must be provided when creating "
                    "a checkpoint.")
            raise exception.InvalidInput(reason=msg)

        if not uuidutils.is_uuid_like(plan_id):
            msg = _("Invalid plan id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        plan = objects.Plan.get_by_id(context, plan_id)
        if not plan:
            raise exception.PlanNotFound(plan_id=plan_id)

        # check the provider_id
        if provider_id != plan.get("provider_id"):
            msg = _("The parameter provider_id is not the same as "
                    "the value in the plan.")
            raise exception.InvalidPlan(reason=msg)

        extra_info = checkpoint.get("extra_info", None)
        if extra_info is not None:
            if not isinstance(extra_info, dict):
                msg = _("The extra_info in checkpoint must be a dict when "
                        "creating a checkpoint.")
                raise exception.InvalidInput(reason=msg)
            elif not all(map(lambda s: isinstance(s, six.string_types),
                             extra_info.keys())):
                msg = _("Key of extra_info in checkpoint must be string when"
                        "creating a checkpoint.")
                raise exception.InvalidInput(reason=msg)

        checkpoint_extra_info = None
        if extra_info is not None:
            checkpoint_extra_info = jsonutils.dumps(extra_info)
        checkpoint_properties = {
            'project_id': context.project_id,
            'status': constants.CHECKPOINT_STATUS_PROTECTING,
            'provider_id': provider_id,
            "protection_plan": {
                "id": plan.get("id"),
                "name": plan.get("name"),
                "resources": plan.get("resources"),
            },
            "extra_info": checkpoint_extra_info
        }
        try:
            checkpoint_id = self.protection_api.protect(context, plan,
                                                        checkpoint_properties)
        except Exception as error:
            msg = _("Create checkpoint failed: %s") % error
            raise exc.HTTPBadRequest(explanation=msg)

        checkpoint_properties['id'] = checkpoint_id

        LOG.info("Create the checkpoint successfully. checkpoint_id:%s",
                 checkpoint_id)
        returnval = self._checkpoint_view_builder.detail(
            req, checkpoint_properties)
        return returnval

    def checkpoints_show(self, req, provider_id, checkpoint_id):
        """Return data about the given checkpoint id."""
        context = req.environ['karbor.context']

        LOG.info("Show checkpoint with id: %s.", checkpoint_id)
        LOG.info("provider_id: %s.", provider_id)

        try:
            checkpoint = self._checkpoint_get(context, provider_id,
                                              checkpoint_id)
        except exception.CheckpointNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show checkpoint request issued successfully.")
        LOG.info("checkpoint: %s", checkpoint)
        retval = self._checkpoint_view_builder.detail(req, checkpoint)
        LOG.info("retval: %s", retval)
        return retval

    def _checkpoint_get(self, context, provider_id, checkpoint_id):
        if not uuidutils.is_uuid_like(provider_id):
            msg = _("Invalid provider id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        if not uuidutils.is_uuid_like(checkpoint_id):
            msg = _("Invalid checkpoint id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            check_policy(context, 'checkpoint_get')
        except exception.PolicyNotAuthorized:
            # raise CheckpointNotFound instead to make sure karbor behaves
            # as it used to
            raise exception.CheckpointNotFound(checkpoint_id=checkpoint_id)

        checkpoint = self.protection_api.show_checkpoint(
            context, provider_id, checkpoint_id)

        if checkpoint is None:
            raise exception.CheckpointNotFound(checkpoint_id=checkpoint_id)

        LOG.info("Checkpoint info retrieved successfully.")
        return checkpoint

    def checkpoints_delete(self, req, provider_id, checkpoint_id):
        """Delete a checkpoint."""
        context = req.environ['karbor.context']

        LOG.info("Delete checkpoint with id: %s.", checkpoint_id)
        LOG.info("provider_id: %s.", provider_id)

        if not uuidutils.is_uuid_like(provider_id):
            msg = _("Invalid provider id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        if not uuidutils.is_uuid_like(checkpoint_id):
            msg = _("Invalid checkpoint id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        check_policy(context, 'checkpoint_delete')
        self.protection_api.delete(context,
                                   provider_id,
                                   checkpoint_id)

        LOG.info("Delete checkpoint request issued successfully.")
        return {}


def create_resource():
    return wsgi.Resource(ProvidersController())
