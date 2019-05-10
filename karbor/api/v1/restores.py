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

"""The restores api."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.api.schemas import restores as restore_schema
from karbor.api import validation
from karbor.common import constants
from karbor.common import notification
from karbor.common.notification import StartNotification
from karbor import exception
from karbor.i18n import _

from karbor import objects
from karbor.objects import base as objects_base
from karbor.policies import restores as restore_policy
from karbor.services.protection import api as protection_api
from karbor import utils

import six

query_restore_filters_opt = cfg.ListOpt(
    'query_restore_filters',
    default=['status'],
    help="Restore filter options which "
    "non-admin user could use to "
    "query restores. Default values "
    "are: ['status']")
CONF = cfg.CONF
CONF.register_opt(query_restore_filters_opt)

LOG = logging.getLogger(__name__)


class RestoreViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "restores"

    def detail(self, request, restore):
        """Detailed view of a single restore."""
        restore_ref = {
            'restore': {
                'id': restore.get('id'),
                'project_id': restore.get('project_id'),
                'provider_id': restore.get('provider_id'),
                'checkpoint_id': restore.get('checkpoint_id'),
                'restore_target': restore.get('restore_target'),
                'parameters': restore.get('parameters'),
                'status': restore.get('status'),
                'resources_status': restore.get('resources_status'),
                'resources_reason': restore.get('resources_reason'),
            }
        }
        return restore_ref

    def detail_list(self, request, restores, restore_count=None):
        """Detailed view of a list of restores."""
        return self._list_view(self.detail, request, restores,
                               restore_count,
                               self._collection_name)

    def _list_view(self, func, request, restores, restore_count,
                   coll_name=_collection_name):
        """Provide a view for a list of restores.

        :param func: Function used to format the restore data
        :param request: API request
        :param restores: List of restores in dictionary format
        :param restore_count: Length of the original list of restores
        :param coll_name: Name of collection, used to generate the next link
                          for a pagination query
        :returns: restore data in dictionary format
        """
        restores_list = [func(request, restore)['restore']
                         for restore in restores]
        restores_links = self._get_collection_links(request,
                                                    restores,
                                                    coll_name,
                                                    restore_count)
        restores_dict = {
            'restores': restores_list
        }
        if restores_links:
            restores_dict['restores_links'] = restores_links

        return restores_dict


class RestoresController(wsgi.Controller):
    """The Restores API controller for the OpenStack API."""

    _view_builder_class = RestoreViewBuilder

    def __init__(self):
        self.protection_api = protection_api.API()
        super(RestoresController, self).__init__()

    def show(self, req, id):
        """Return data about the given restore."""
        context = req.environ['karbor.context']

        LOG.info("Show restore with id: %s", id, context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid restore id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            restore = self._restore_get(context, id)
        except exception.RestoreNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show restore request issued successfully.",
                 resource={'id': restore.id})
        return self._view_builder.detail(req, restore)

    def index(self, req):
        """Returns a list of restores, transformed through view builder."""
        context = req.environ['karbor.context']

        LOG.info("Show restore list", context=context)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        utils.remove_invalid_filter_options(
            context,
            filters,
            self._get_restore_filter_options())

        utils.check_filters(filters)
        restores = self._get_all(context, marker, limit,
                                 sort_keys=sort_keys,
                                 sort_dirs=sort_dirs,
                                 filters=filters,
                                 offset=offset)

        retval_restores = self._view_builder.detail_list(req, restores)

        LOG.info("Show restore list request issued successfully.")

        return retval_restores

    def _get_all(self, context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
        context.can(restore_policy.GET_ALL_POLICY)

        if filters is None:
            filters = {}

        all_tenants = utils.get_bool_param('all_tenants', filters)

        if filters:
            LOG.debug("Searching by: %s.", six.text_type(filters))

        if context.is_admin and all_tenants:
            # Need to remove all_tenants to pass the filtering below.
            del filters['all_tenants']
            restores = objects.RestoreList.get_all(
                context, marker, limit,
                sort_keys=sort_keys,
                sort_dirs=sort_dirs,
                filters=filters,
                offset=offset)
        else:
            restores = objects.RestoreList.get_all_by_project(
                context, context.project_id, marker, limit,
                sort_keys=sort_keys, sort_dirs=sort_dirs, filters=filters,
                offset=offset)

        LOG.info("Get all restores completed successfully.")
        return restores

    def _get_restore_filter_options(self):
        """Return restores search options allowed by non-admin."""
        return CONF.query_restore_filters

    @validation.schema(restore_schema.create)
    def create(self, req, body):
        """Creates a new restore."""

        LOG.debug('Create restore request body: %s', body)
        context = req.environ['karbor.context']
        context.can(restore_policy.CREATE_POLICY)
        context.notification = notification.KarborRestoreCreate(
            context, request=req)
        restore = body['restore']
        LOG.debug('Create restore request : %s', restore)

        parameters = restore.get("parameters")
        restore_auth = restore.get("restore_auth", None)
        restore_properties = {
            'project_id': context.project_id,
            'provider_id': restore.get('provider_id'),
            'checkpoint_id': restore.get('checkpoint_id'),
            'restore_target': restore.get('restore_target'),
            'parameters': parameters,
            'status': constants.RESTORE_STATUS_IN_PROGRESS,
        }

        restoreobj = objects.Restore(context=context,
                                     **restore_properties)
        restoreobj.create()
        LOG.debug('call restore RPC  : restoreobj:%s', restoreobj)

        # call restore rpc API of protection service
        try:
            with StartNotification(context, parameters=parameters):
                self.protection_api.restore(context, restoreobj, restore_auth)
        except exception.AccessCheckpointNotAllowed as error:
            raise exc.HTTPForbidden(explanation=error.msg)
        except Exception:
            # update the status of restore
            update_dict = {
                "status": constants.RESTORE_STATUS_FAILURE
            }
            context.can(restore_policy.UPDATE_POLICY, restoreobj)
            restoreobj = self._restore_update(context,
                                              restoreobj.get("id"),
                                              update_dict)

        retval = self._view_builder.detail(req, restoreobj)

        return retval

    def _restore_get(self, context, restore_id):
        if not uuidutils.is_uuid_like(restore_id):
            msg = _("Invalid restore id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        restore = objects.Restore.get_by_id(context, restore_id)
        try:
            context.can(restore_policy.GET_POLICY, restore)
        except exception.PolicyNotAuthorized:
            # raise RestoreNotFound instead to make sure karbor behaves
            # as it used to
            raise exception.RestoreNotFound(restore_id=restore_id)
        LOG.info("Restore info retrieved successfully.")
        return restore

    def _restore_update(self, context, restore_id, fields):
        try:
            restore = self._restore_get(context, restore_id)
        except exception.RestoreNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        if isinstance(restore, objects_base.KarborObject):
            restore.update(fields)
            restore.save()
            LOG.info("restore updated successfully.")
            return restore
        else:
            msg = _("The parameter restore must be a object of "
                    "KarborObject class.")
            raise exception.InvalidInput(reason=msg)


def create_resource():
    return wsgi.Resource(RestoresController())
