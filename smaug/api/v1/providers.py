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
from oslo_utils import uuidutils

from webob import exc

from smaug.api import common
from smaug.api.openstack import wsgi
from smaug import exception
from smaug.i18n import _, _LI

import smaug.policy
from smaug.services.protection import api as protection_api
from smaug import utils

import six

query_provider_filters_opt = \
    cfg.ListOpt('query_provider_filters',
                default=['name', 'description'],
                help="Provider filter options which "
                     "non-admin user could use to "
                     "query providers. Default values "
                     "are: ['name', 'description']")

query_checkpoint_filters_opt = \
    cfg.ListOpt('query_checkpoint_filters',
                default=['project_id', 'status'],
                help="Checkpoint filter options which "
                     "non-admin user could use to "
                     "query checkpoints. Default values "
                     "are: ['project_id', 'status']")

CONF = cfg.CONF
CONF.register_opt(query_provider_filters_opt)
CONF.register_opt(query_checkpoint_filters_opt)

LOG = logging.getLogger(__name__)


def check_policy(context, action):
    target = {
        'project_id': context.project_id,
        'user_id': context.user_id,
    }
    _action = 'provider:%s' % action
    smaug.policy.enforce(context, _action, target)


class ProviderViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "providers"

    def __init__(self):
        """Initialize view builder."""
        super(ProviderViewBuilder, self).__init__()

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


class ProvidersController(wsgi.Controller):
    """The Providers API controller for the OpenStack API."""

    _view_builder_class = ProviderViewBuilder

    def __init__(self):
        self.protection_api = protection_api.API()
        super(ProvidersController, self).__init__()

    def show(self, req, id):
        """Return data about the given provider id."""
        context = req.environ['smaug.context']

        LOG.info(_LI("Show provider with id: %s"), id)

        try:
            provider = self._provider_get(context, id)
        except exception.ProviderNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info(_LI("Show provider request issued successfully."),
                 resource={'id': provider.get("id")})
        return self._view_builder.detail(req, provider)

    def index(self, req):
        """Returns a list of providers, transformed through view builder."""
        context = req.environ['smaug.context']

        LOG.info(_LI("Show provider list"), context=context)

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

        LOG.info(_LI("Show provider list request issued successfully."))

        return retval_providers

    def _get_all(self, context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
        check_policy(context, 'get_all')

        if filters is None:
            filters = {}

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

        if context.is_admin:
            providers = self.protection_api.list_providers(
                context, marker, limit,
                sort_keys=sort_keys,
                sort_dirs=sort_dirs,
                filters=filters,
                offset=offset)
        else:
            msg = _('user must be an administrator')
            raise exception.InvalidInput(reason=msg)

        LOG.info(_LI("Get all providers completed successfully."))
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
            # raise ProviderNotFound instead to make sure smaug behaves
            # as it used to
            raise exception.ProviderNotFound(provider_id=provider_id)

        provider = self.protection_api.show_provider(context, provider_id)

        LOG.info(_LI("Provider info retrieved successfully."))
        return provider


def create_resource():
    return wsgi.Resource(ProvidersController())
