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

"""The service management api."""
from oslo_log import log as logging
from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.policies import services as service_policy
from karbor import utils

LOG = logging.getLogger(__name__)

SERVICES_CAN_BE_UPDATED = ['karbor-operationengine']


class ServiceViewBuilder(common.ViewBuilder):
    """Model a server API response as a python dictionary."""

    _collection_name = "services"

    def detail(self, request, service):
        """Detailed view of a single service."""
        service_ref = {
            'service': {
                'id': service.get('id'),
                'binary': service.get('binary'),
                'host': service.get('host'),
                'status': 'disabled' if service.get('disabled') else 'enabled',
                'state': 'up' if utils.service_is_up(service) else 'down',
                'updated_at': service.get('updated_at'),
                'disabled_reason': service.get('disabled_reason')
            }
        }
        return service_ref

    def detail_list(self, request, services, service_count=None):
        """Detailed view of a list of services."""
        return self._list_view(self.detail, request, services)

    def _list_view(self, func, request, services):
        """Provide a view for a list of service.

        :param func: Function used to format the service data
        :param request: API request
        :param services: List of services in dictionary format
        :returns: Service data in dictionary format
        """
        services_list = [func(request, service)['service']
                         for service in services]
        services_dict = {
            "services": services_list
        }

        return services_dict


class ServiceController(wsgi.Controller):
    """The Service Management API controller for the OpenStack API."""

    _view_builder_class = ServiceViewBuilder

    def __init__(self):
        super(ServiceController, self).__init__()

    def index(self, req):
        """Returns a list of services

        transformed through view builder.
        """
        context = req.environ['karbor.context']
        context.can(service_policy.GET_ALL_POLICY)
        host = req.GET['host'] if 'host' in req.GET else None
        binary = req.GET['binary'] if 'binary' in req.GET else None
        try:
            services = objects.ServiceList.get_all_by_args(
                context, host, binary)
        except Exception as e:
            msg = (_('List service failed, reason: %s') % e)
            raise exc.HTTPBadRequest(explanation=msg)
        return self._view_builder.detail_list(req, services)

    def update(self, req, id, body):
        """Enable/Disable scheduling for a service"""

        context = req.environ['karbor.context']
        context.can(service_policy.UPDATE_POLICY)
        try:
            service = objects.Service.get_by_id(context, id)
        except exception.ServiceNotFound as e:
            raise exc.HTTPNotFound(explanation=e.message)

        if service.binary not in SERVICES_CAN_BE_UPDATED:
            msg = (_('Updating a %(binary)s service is not supported. Only '
                     'karbor-operationengine services can be updated.') %
                   {'binary': service.binary})
            raise exc.HTTPBadRequest(explanation=msg)

        if 'status' in body:
            if body['status'] == 'enabled':
                if body.get('disabled_reason'):
                    msg = _("Specifying 'disabled_reason' with status "
                            "'enabled' is invalid.")
                    raise exc.HTTPBadRequest(explanation=msg)
                service.disabled = False
                service.disabled_reason = None
            elif body['status'] == 'disabled':
                service.disabled = True
                service.disabled_reason = body.get('disabled_reason')
        service.save()
        return self._view_builder.detail(req, service)


def create_resource():
    return wsgi.Resource(ServiceController())
