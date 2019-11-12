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

"""The verification api."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.api.schemas import verifications as verification_schema
from karbor.api import validation
from karbor.common import constants
from karbor import exception
from karbor.i18n import _

from karbor import objects
from karbor.objects import base as objects_base
from karbor.policies import verifications as verification_policy
from karbor.services.protection import api as protection_api
from karbor import utils

import six

query_verification_filters_opt = cfg.ListOpt(
    'query_verification_filters',
    default=['status'],
    help="Verification filter options which "
    "non-admin user could use to "
    "query verifications. Default values "
    "are: ['status']")
CONF = cfg.CONF
CONF.register_opt(query_verification_filters_opt)

LOG = logging.getLogger(__name__)


class VerificationViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "verifications"

    def detail(self, request, verification):
        """Detailed view of a single verification."""
        verification_ref = {
            'verification': {
                'id': verification.get('id'),
                'project_id': verification.get('project_id'),
                'provider_id': verification.get('provider_id'),
                'checkpoint_id': verification.get('checkpoint_id'),
                'parameters': verification.get('parameters'),
                'status': verification.get('status'),
                'resources_status': verification.get('resources_status'),
                'resources_reason': verification.get('resources_reason'),
            }
        }
        return verification_ref

    def detail_list(self, request, verifications, verification_count=None):
        """Detailed view of a list of verifications."""
        return self._list_view(self.detail, request, verifications,
                               verification_count,
                               self._collection_name)

    def _list_view(self, func, request, verifications, verification_count,
                   coll_name=_collection_name):
        """Provide a view for a list of verifications.

        :param func: Function used to format the verification data
        :param request: API request
        :param verifications: List of verifications in dictionary format
        :param verification_count: Length of the original list of verifications
        :param coll_name: Name of collection, used to generate the next link
                          for a pagination query
        :returns: verification data in dictionary format
        """
        verifications_list = [func(request, verification)['verification']
                              for verification in verifications]
        verifications_links = self._get_collection_links(request,
                                                         verifications,
                                                         coll_name,
                                                         verification_count)
        verifications_dict = {
            'verifications': verifications_list
        }
        if verifications_links:
            verifications_dict['verifications_links'] = verifications_links

        return verifications_dict


class VerificationsController(wsgi.Controller):
    """The verifications API controller for the OpenStack API."""

    _view_builder_class = VerificationViewBuilder

    def __init__(self):
        self.protection_api = protection_api.API()
        super(VerificationsController, self).__init__()

    def show(self, req, id):
        """Return data about the given verification."""
        context = req.environ['karbor.context']

        LOG.info("Show verification with id: %s", id, context=context)

        try:
            verification = self._verification_get(context, id)
        except exception.VerificationNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show verification request issued successfully.",
                 resource={'id': verification.id})
        return self._view_builder.detail(req, verification)

    def index(self, req):
        """Returns a list of verifications."""
        context = req.environ['karbor.context']

        LOG.info("Show verification list", context=context)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        utils.remove_invalid_filter_options(
            context,
            filters,
            CONF.query_verification_filters)

        utils.check_filters(filters)
        verifications = self._get_all(context, marker, limit,
                                      sort_keys=sort_keys,
                                      sort_dirs=sort_dirs,
                                      filters=filters,
                                      offset=offset)
        retval_verifications = self._view_builder.detail_list(req,
                                                              verifications)

        LOG.info("Show verification list request issued successfully.")

        return retval_verifications

    def _get_all(self, context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
        context.can(verification_policy.GET_ALL_POLICY)

        if filters is None:
            filters = {}

        all_tenants = utils.get_bool_param('all_tenants', filters)

        if filters:
            LOG.debug("Searching by: %s.", six.text_type(filters))

        if context.is_admin and all_tenants:
            # Need to remove all_tenants to pass the filtering below.
            del filters['all_tenants']
            verifications = objects.VerificationList.get_all(
                context, marker, limit,
                sort_keys=sort_keys,
                sort_dirs=sort_dirs,
                filters=filters,
                offset=offset)
        else:
            verifications = objects.VerificationList.get_all_by_project(
                context, context.project_id, marker, limit,
                sort_keys=sort_keys, sort_dirs=sort_dirs, filters=filters,
                offset=offset)

        LOG.info("Get all verifications completed successfully.")
        return verifications

    @validation.schema(verification_schema.create)
    def create(self, req, body):
        """Creates a new verification."""

        LOG.debug('Create verification request body: %s', body)
        context = req.environ['karbor.context']
        context.can(verification_policy.CREATE_POLICY)
        verification = body['verification']
        LOG.debug('Create verification request : %s', verification)

        parameters = verification.get("parameters")

        verification_properties = {
            'project_id': context.project_id,
            'provider_id': verification.get('provider_id'),
            'checkpoint_id': verification.get('checkpoint_id'),
            'parameters': parameters,
            'status': constants.VERIFICATION_STATUS_IN_PROGRESS,
        }

        verification_obj = objects.Verification(context=context,
                                                **verification_properties)
        verification_obj.create()

        try:
            self.protection_api.verification(context, verification_obj)
        except Exception:
            update_dict = {
                "status": constants.VERIFICATION_STATUS_FAILURE
            }
            verification_obj = self._verification_update(
                context,
                verification_obj.get("id"),
                update_dict)

        retval = self._view_builder.detail(req, verification_obj)

        return retval

    def _verification_get(self, context, verification_id):
        if not uuidutils.is_uuid_like(verification_id):
            msg = _("Invalid verification id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        verification = objects.Verification.get_by_id(context, verification_id)
        try:
            context.can(verification_policy.GET_POLICY, verification)
        except exception.PolicyNotAuthorized:
            # raise VerificationNotFound instead to make sure karbor behaves
            # as it used to
            raise exception.VerificationNotFound(
                verification_id=verification_id)
        LOG.info("Verification info retrieved successfully.")
        return verification

    def _verification_update(self, context, verification_id, fields):
        try:
            verification = self._verification_get(context, verification_id)
        except exception.VerificationNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        if isinstance(verification, objects_base.KarborObject):
            verification.update(fields)
            verification.save()
            LOG.info("The verification updated successfully.")
            return verification
        else:
            msg = _("The parameter verification must be a object of "
                    "KarborObject class.")
            raise exception.InvalidInput(reason=msg)


def create_resource():
    return wsgi.Resource(VerificationsController())
