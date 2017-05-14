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

"""The protectables api."""
from oslo_config import cfg
from oslo_log import log as logging

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor import exception
from karbor.i18n import _

import karbor.policy
from karbor.services.protection import api as protection_api
from karbor import utils

import six

query_instance_filters_opts = [
    cfg.ListOpt(
        'query_instance_filters',
        default=['status'],
        help=(
            "Instance filter options which non-admin user could use to "
            "query instances. Default values are: ['status']"
        )
    ),
]
CONF = cfg.CONF
CONF.register_opts(query_instance_filters_opts)
LOG = logging.getLogger(__name__)


def check_policy(context, action):
    target = {
        'project_id': context.project_id,
        'user_id': context.user_id,
    }
    _action = 'protectable:%s' % action
    karbor.policy.enforce(context, _action, target)


class ProtectableViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "protectables"

    def show(self, request, protectable_type):
        """Detailed view of a single protectable_type."""
        protectable_type_ref = {
            'protectable_type': {
                'name': protectable_type.get('name'),
                'dependent_types': protectable_type.get('dependent_types'),
            }
        }
        return protectable_type_ref

    def detail(self, request, instance):
        """Detailed view of a single instance."""
        instance_ref = {
            'instance': {
                'id': instance.get('id'),
                'type': instance.get('type'),
                'name': instance.get('name'),
                'extra_info': instance.get('extra_info'),
                'dependent_resources': instance.get('dependent_resources'),
            }
        }
        return instance_ref

    def detail_list(self, request, instances, instance_count=None):
        """Detailed view of a list of instances."""
        return self._list_view(self.detail, request, instances,
                               instance_count,
                               'instances')

    def _list_view(self, func, request, instances, instance_count,
                   coll_name=_collection_name):
        """Provide a view for a list of instance.

        :param func: Function used to format the instance data
        :param request: API request
        :param instances: List of instances in dictionary format
        :param instance_count: Length of the original list of instances
        :param coll_name: Name of collection, used to generate the next link
                          for a pagination query
        :returns: instance data in dictionary format
        """
        instances_list = [func(request, instance)['instance']
                          for instance in instances]
        instances_links = self._get_collection_links(request,
                                                     instances,
                                                     coll_name,
                                                     instance_count)
        instances_dict = {
            "instances": instances_list
        }
        if instances_links:
            instances_dict['instances_links'] = instances_links

        return instances_dict


class ProtectablesController(wsgi.Controller):
    """The Protectables API controller for the OpenStack API."""

    _view_builder_class = ProtectableViewBuilder

    def __init__(self):
        self.protection_api = protection_api.API()
        super(ProtectablesController, self).__init__()

    def show(self, req, id):
        """Return data about the given protectable_type."""
        context = req.environ['karbor.context']
        protectable_type = id

        LOG.info("Show the information of a given protectable type: %s",
                 protectable_type)

        protectable_types = self._get_all(context)

        if protectable_type not in protectable_types:
            msg = _("Invalid protectable type provided.")
            raise exception.InvalidInput(reason=msg)

        check_policy(context, 'get')
        try:
            retval_protectable_type = self.protection_api.\
                show_protectable_type(context, protectable_type)
        except exception.ProtectableTypeNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)

        LOG.info("Show the protectable type information issued successfully.")
        return self._view_builder.show(req, retval_protectable_type)

    def index(self, req):
        """Returns a list of protectable_types,

        transformed through view builder.
        """
        context = req.environ['karbor.context']
        LOG.info("Show protectable type list", context=context)

        protectable_types = self._get_all(context)
        retval_protectable_types = {
            "protectable_type": protectable_types
        }

        LOG.info("Show protectable type list request issued successfully.")
        return retval_protectable_types

    def _get_all(self, context):
        check_policy(context, 'get_all')

        protectable_types = self.protection_api.list_protectable_types(context)

        LOG.info("Get all protectable types completed successfully.")
        return protectable_types

    def instances_index(self, req, protectable_type):
        """Return data about the given protectable_type."""
        context = req.environ['karbor.context']
        LOG.info("Show the instances of a given protectable type: %s",
                 protectable_type)

        params = req.params.copy()
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params
        utils.check_filters(filters)
        parameters = filters.get("parameters", None)

        if parameters is not None:
            if not isinstance(parameters, dict):
                msg = _("The parameters must be a dict.")
                raise exception.InvalidInput(reason=msg)

        utils.remove_invalid_filter_options(
            context,
            filters,
            self._get_instance_filter_options())

        protectable_types = self._get_all(context)

        if protectable_type not in protectable_types:
            msg = _("Invalid protectable type provided.")
            raise exception.InvalidInput(reason=msg)

        instances = self._instances_get_all(
            context, protectable_type, marker, limit,
            sort_keys=sort_keys, sort_dirs=sort_dirs,
            filters=filters, offset=offset, parameters=parameters)

        for instance in instances:
            protectable_id = instance.get("id")
            instance["type"] = protectable_type
            if protectable_id is None:
                raise exception.InvalidProtectableInstance()
            dependents = self.protection_api.list_protectable_dependents(
                context, protectable_id, protectable_type)
            instance["dependent_resources"] = dependents

        retval_instances = self._view_builder.detail_list(req, instances)

        return retval_instances

    def _instances_get_all(self, context, protectable_type, marker=None,
                           limit=None, sort_keys=None, sort_dirs=None,
                           filters=None, offset=None, parameters=None):
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

        instances = self.protection_api.list_protectable_instances(
            context, protectable_type, marker, limit,
            sort_keys=sort_keys,
            sort_dirs=sort_dirs,
            filters=filters,
            offset=offset,
            parameters=parameters)

        LOG.info("Get all instances completed successfully.")
        return instances

    def _get_instance_filter_options(self):
        """Return instance search options allowed by non-admin."""
        return CONF.query_instance_filters

    def instances_show(self, req, protectable_type, protectable_id):
        """Return a instance about the given protectable_type and id."""

        context = req.environ['karbor.context']
        params = req.params.copy()
        utils.check_filters(params)
        parameters = params.get("parameters", None)

        LOG.info("Show the instance of a given protectable type: %s",
                 protectable_type)

        if parameters is not None:
            if not isinstance(parameters, dict):
                msg = _("The parameters must be a dict.")
                raise exception.InvalidInput(reason=msg)

        protectable_types = self._get_all(context)

        if protectable_type not in protectable_types:
            msg = _("Invalid protectable type provided.")
            raise exception.InvalidInput(reason=msg)

        try:
            instance = self.protection_api.show_protectable_instance(
                context, protectable_type, protectable_id,
                parameters=parameters)
        except exception.ProtectableResourceNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)
        except Exception as err:
            raise exc.HTTPInternalServerError(
                explanation=six.text_type(err))

        if instance is None:
            msg = _("The instance doesn't exist.")
            raise exc.HTTPInternalServerError(explanation=msg)

        dependents = self.protection_api.list_protectable_dependents(
            context, protectable_id, protectable_type)
        instance["dependent_resources"] = dependents

        retval_instance = self._view_builder.detail(req, instance)
        return retval_instance


def create_resource():
    return wsgi.Resource(ProtectablesController())
