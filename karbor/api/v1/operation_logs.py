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

"""The operation_logs api."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor import exception
from karbor.i18n import _

from karbor import objects
from karbor.policies import operation_logs as operation_log_policy
from karbor.services.operationengine import api as operationengine_api
from karbor.services.protection import api as protection_api
from karbor import utils

import six

query_operation_log_filters_opt = cfg.ListOpt(
    'query_operation_log_filters',
    default=['checkpoint_id', 'plan_id', 'restore_id', 'status'],
    help="Operation log filter options which "
    "non-admin user could use to "
    "query operation_logs. Default values "
    "are: ['checkpoint_id', 'plan_id', 'restore_id', 'status']")

CONF = cfg.CONF
CONF.register_opt(query_operation_log_filters_opt)

LOG = logging.getLogger(__name__)


class OperationLogViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "operation_logs"

    def detail(self, request, operation_log):
        """Detailed view of a single operation_log."""

        operation_log_ref = {
            'operation_log': {
                'id': operation_log.get('id'),
                'operation_type': operation_log.get('operation_type'),
                'checkpoint_id': operation_log.get('checkpoint_id'),
                'plan_id': operation_log.get('plan_id'),
                'provider_id': operation_log.get('provider_id'),
                'restore_id': operation_log.get('restore_id'),
                'scheduled_operation_id': operation_log.get(
                    'scheduled_operation_id'),
                'status': operation_log.get('status'),
                'started_at': operation_log.get('started_at'),
                'ended_at': operation_log.get('ended_at'),
                'error_info': operation_log.get('error_info'),
                'extra_info': operation_log.get('extra_info'),
            }
        }
        return operation_log_ref

    def detail_list(self, request, operation_logs,
                    operation_log_count=None):
        """Detailed view of a list of operation_logs."""
        return self._list_view(self.detail, request, operation_logs,
                               operation_log_count,
                               self._collection_name)

    def _list_view(self, func, request, operation_logs,
                   operation_log_count,
                   coll_name=_collection_name):
        """Provide a view for a list of operation_logs.

        """
        operation_logs_list = [func(
            request, operation_log)['operation_log']
            for operation_log in operation_logs]
        operation_logs_links = self._get_collection_links(
            request, operation_logs, coll_name, operation_log_count)
        operation_logs_dict = {}
        operation_logs_dict['operation_logs'] = operation_logs_list
        if operation_logs_links:
            operation_logs_dict['operation_logs_links'] = (
                operation_logs_links)

        return operation_logs_dict


class OperationLogsController(wsgi.Controller):
    """The operation_log API controller for the OpenStack API."""

    _view_builder_class = OperationLogViewBuilder

    def __init__(self):
        self.operationengine_api = operationengine_api.API()
        self.protection_api = protection_api.API()
        super(OperationLogsController, self).__init__()

    def show(self, req, id):
        """Return data about the given OperationLogs."""
        context = req.environ['karbor.context']

        LOG.info("Show operation log with id: %s", id, context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid operation log id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            operation_log = self._operation_log_get(context, id)
        except exception.OperationLogFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show operation log request issued successfully.")
        return self._view_builder.detail(req, operation_log)

    def index(self, req):
        """Returns a list of operation_logs.

        """
        context = req.environ['karbor.context']

        LOG.info("Show operation log list", context=context)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        utils.remove_invalid_filter_options(
            context,
            filters,
            self._get_operation_log_filter_options())

        utils.check_filters(filters)
        operation_logs = self._get_all(context, marker, limit,
                                       sort_keys=sort_keys,
                                       sort_dirs=sort_dirs,
                                       filters=filters,
                                       offset=offset)

        retval_operation_logs = self._view_builder.detail_list(
            req, operation_logs)

        LOG.info("Show operation_log list request issued "
                 "successfully.")

        return retval_operation_logs

    def _get_all(self, context, marker=None, limit=None, sort_keys=None,
                 sort_dirs=None, filters=None, offset=None):
        context.can(operation_log_policy.GET_ALL_POLICY)

        if filters is None:
            filters = {}

        all_tenants = utils.get_bool_param('all_tenants', filters)

        if filters:
            LOG.debug("Searching by: %s.", six.text_type(filters))

        if context.is_admin and all_tenants:
            # Need to remove all_tenants to pass the filtering below.
            del filters['all_tenants']
            operation_logs = objects.OperationLogList.get_all(
                context, marker, limit,
                sort_keys=sort_keys,
                sort_dirs=sort_dirs,
                filters=filters,
                offset=offset)
        else:
            operation_logs = objects.OperationLogList.get_all_by_project(
                context, context.project_id, marker, limit,
                sort_keys=sort_keys, sort_dirs=sort_dirs, filters=filters,
                offset=offset)

        LOG.info("Get all operation_logs completed successfully.")
        return operation_logs

    def _get_operation_log_filter_options(self):
        """Return operation_log search options allowed by non-admin."""
        return CONF.query_operation_log_filters

    def _operation_log_get(self, context, operation_log_id):
        if not uuidutils.is_uuid_like(operation_log_id):
            msg = _("Invalid operation_log id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        operation_log = objects.OperationLog.get_by_id(
            context, operation_log_id)
        try:
            context.can(operation_log_policy.GET_POLICY, operation_log)
        except exception.PolicyNotAuthorized:
            raise exception.OperationLogFound(
                operation_log_id=operation_log_id)
        LOG.info("Operation log info retrieved successfully.")
        return operation_log


def create_resource():
    return wsgi.Resource(OperationLogsController())
