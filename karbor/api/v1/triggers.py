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

"""The triggers api."""

from datetime import datetime
from oslo_log import log as logging
from oslo_utils import uuidutils
from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor import policy
from karbor.services.operationengine import api as operationengine_api
from karbor import utils

LOG = logging.getLogger(__name__)


def check_policy(context, action, target_obj=None):
    _action = 'trigger:%s' % action
    policy.enforce(context, _action, target_obj)


class TriggerViewBuilder(common.ViewBuilder):
    """Model a trigger API response as a python dictionary."""

    _collection_name = "triggers"

    def detail(self, request, trigger):
        """Detailed view of a single trigger."""

        trigger_ref = {
            'trigger_info': {
                'id': trigger.get('id'),
                'name': trigger.get('name'),
                'type': trigger.get('type'),
                'properties': trigger.get('properties'),
            }
        }
        return trigger_ref

    def detail_list(self, request, triggers):
        """Detailed view of a list of triggers."""
        return self._list_view(self.detail, request, triggers)

    def _list_view(self, func, request, triggers):
        triggers_list = [func(request, item)['trigger_info']
                         for item in triggers]

        triggers_links = self._get_collection_links(request,
                                                    triggers,
                                                    self._collection_name,
                                                    )
        ret = {'triggers': triggers_list}
        if triggers_links:
            ret['triggers_links'] = triggers_links

        return ret


class TriggersController(wsgi.Controller):
    """The Triggers API controller for the OpenStack API."""

    _view_builder_class = TriggerViewBuilder

    def __init__(self):
        self.operationengine_api = operationengine_api.API()
        super(TriggersController, self).__init__()

    def create(self, req, body):
        """Creates a new trigger."""

        LOG.debug('Create trigger start')

        if not self.is_valid_body(body, 'trigger_info'):
            raise exc.HTTPUnprocessableEntity()
        LOG.debug('Create a trigger, request body: %s', body)

        context = req.environ['karbor.context']
        check_policy(context, 'create')
        trigger_info = body['trigger_info']

        trigger_name = trigger_info.get("name", None)
        trigger_type = trigger_info.get("type", None)
        trigger_property = trigger_info.get("properties", None)
        if not trigger_name or not trigger_type or not trigger_property:
            msg = _("Trigger name or type or property is not provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        self.validate_name_and_description(trigger_info)

        trigger_property.setdefault(
            'start_time', datetime.utcnow().replace(microsecond=0))
        trigger_definition = {
            'id': uuidutils.generate_uuid(),
            'name': trigger_name,
            'project_id': context.project_id,
            'type': trigger_type,
            'properties': trigger_property,
        }
        try:
            trigger = objects.Trigger(context=context, **trigger_definition)
            self.operationengine_api.create_trigger(context, trigger)
            trigger.create()
        except exception.Invalid as ex:
            raise exc.HTTPBadRequest(explanation=ex.msg)
        except Exception as ex:
            self._raise_unknown_exception(ex)

        return self._view_builder.detail(req, trigger)

    def delete(self, req, id):
        """Delete a trigger."""

        LOG.debug('Delete trigger(%s) start', id)

        context = req.environ['karbor.context']
        trigger = self._get_trigger_by_id(context, id)

        check_policy(context, 'delete', trigger)

        try:
            operations = objects.ScheduledOperationList.get_by_filters(
                context, {"trigger_id": id}, limit=1)
        except Exception as ex:
            self._raise_unknown_exception(ex)

        if operations:
            msg = _("Trigger is being used by one or more operations")
            raise exc.HTTPFailedDependency(explanation=msg)

        try:
            self.operationengine_api.delete_trigger(context, id)
        except exception.TriggerNotFound as ex:
            pass
        except (exception.DeleteTriggerNotAllowed,
                Exception) as ex:
            self._raise_unknown_exception(ex)

        trigger.destroy()

    def update(self, req, id, body):
        """Update a trigger"""

        LOG.debug('Update trigger(%s) start', id)

        context = req.environ['karbor.context']
        trigger = self._get_trigger_by_id(context, id)

        check_policy(context, 'update', trigger)

        trigger_info = body['trigger_info']
        trigger_name = trigger_info.get("name", None)
        trigger_property = trigger_info.get("properties", None)

        if trigger_name:
            self.validate_name_and_description(trigger_info)
            trigger.name = trigger_name

        if trigger_property:
            start_time = trigger_property.get('start_time', None)
            if not start_time:
                msg = (_("start_time should be supplied"))
                raise exc.HTTPBadRequest(explanation=msg)
            try:
                trigger.properties = trigger_property
                self.operationengine_api.update_trigger(context, trigger)
            except exception.InvalidInput as ex:
                raise exc.HTTPBadRequest(explanation=ex.msg)
            except (exception.TriggerNotFound, Exception) as ex:
                self._raise_unknown_exception(ex)
        try:
            trigger.save()
        except Exception as ex:
            self._raise_unknown_exception(ex)

        return self._view_builder.detail(req, trigger)

    def show(self, req, id):
        """Return data about the given trigger."""

        LOG.debug('Get trigger(%s) start', id)

        context = req.environ['karbor.context']
        trigger = self._get_trigger_by_id(context, id)

        check_policy(context, 'get', trigger)
        return self._view_builder.detail(req, trigger)

    def index(self, req):
        """Returns a list of triggers, transformed through view builder."""

        context = req.environ['karbor.context']
        check_policy(context, 'list')

        params = req.params.copy()
        LOG.debug('List triggers start, params=%s', params)
        marker, limit, offset = common.get_pagination_params(params)
        sort_keys, sort_dirs = common.get_sort_params(params)
        filters = params

        valid_filters = ["all_tenants", "name", "type", "properties"]
        utils.remove_invalid_filter_options(context, filters, valid_filters)
        utils.check_filters(filters)

        all_tenants = utils.get_bool_param("all_tenants", filters)
        if not (context.is_admin and all_tenants):
            filters["project_id"] = context.project_id

        try:
            triggers = objects.TriggerList.get_by_filters(
                context, filters, limit, marker, sort_keys, sort_dirs)
        except Exception as ex:
            self._raise_unknown_exception(ex)

        return self._view_builder.detail_list(req, triggers)

    def _get_trigger_by_id(self, context, id):
        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid trigger id provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        try:
            trigger = objects.Trigger.get_by_id(context, id)
        except exception.TriggerNotFound as error:
            raise exc.HTTPNotFound(explanation=error.msg)
        except Exception as ex:
            self._raise_unknown_exception(ex)

        return trigger

    def _raise_unknown_exception(self, exception_instance):
        LOG.exception('An unknown exception happened')

        value = exception_instance.msg if isinstance(
            exception_instance, exception.KarborException) else type(
            exception_instance)
        msg = (_('Unexpected API Error. Please report this at '
                 'http://bugs.launchpad.net/karbor/ and attach the '
                 'Karbor API log if possible.\n%s') % value)
        raise exc.HTTPInternalServerError(explanation=msg)


def create_resource():
    return wsgi.Resource(TriggersController())
