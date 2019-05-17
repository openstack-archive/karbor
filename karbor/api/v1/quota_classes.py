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

"""The Quota Class api."""

from oslo_config import cfg
from oslo_log import log as logging

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.api.schemas import quota_classes as quota_class_schema
from karbor.api import validation
from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor.policies import quota_classes as quota_class_policy

from karbor import quota


QUOTAS = quota.QUOTAS
CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class QuotaClassesViewBuilder(common.ViewBuilder):
    """Model a Quota Class API response as a python dictionary."""

    _collection_name = "quota_class"

    def detail_list(self, request, quota, quota_class=None):
        """Detailed view of a single quota class."""
        keys = (
            'plans',
            'checkpoints',
        )
        view = {key: quota.get(key) for key in keys}
        if quota_class:
            view['id'] = quota_class
        return {self._collection_name: view}


class QuotaClassesController(wsgi.Controller):
    """The Quota Class API controller for the OpenStack API."""

    _view_builder_class = QuotaClassesViewBuilder

    def __init__(self):
        super(QuotaClassesController, self).__init__()

    def show(self, req, id):
        """Return data about the given quota class id."""
        context = req.environ['karbor.context']
        LOG.debug("Show quota class with name: %s", id, context=context)
        quota_class_name = id
        context.can(quota_class_policy.GET_POLICY)
        try:
            quota_class = QUOTAS.get_class_quotas(context,
                                                  quota_class_name)
        except exception.NotAuthorized:
            raise exc.HTTPForbidden()

        LOG.debug("Show quota class request issued successfully.",
                  resource={'id': id})
        return self._view_builder.detail_list(req, quota_class,
                                              quota_class_name)

    @validation.schema(quota_class_schema.update)
    def update(self, req, id, body):
        context = req.environ['karbor.context']

        LOG.info("Update quota class with name: %s", id,
                 context=context)
        context.can(quota_class_policy.UPDATE_POLICY)

        quota_class_name = id
        bad_keys = []
        for key, value in body.get('quota_class', {}).items():
            if key not in QUOTAS:
                bad_keys.append(key)
                continue
            if key in QUOTAS and value:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    msg = _("Quota '%(value)s' for %(key)s should be "
                            "integer.") % {'value': value, 'key': key}
                    LOG.warning(msg)
                    raise exc.HTTPBadRequest(explanation=msg)

        for key in body['quota_class'].keys():
            if key in QUOTAS:
                value = int(body['quota_class'][key])
                self._validate_quota_limit(value)
                try:
                    db.quota_class_update(
                        context, quota_class_name, key, value)
                except exception.QuotaClassNotFound:
                    db.quota_class_create(
                        context, quota_class_name, key, value)
                except exception.AdminRequired:
                    raise exc.HTTPForbidden()

        LOG.info("Update quota class successfully.",
                 resource={'id': quota_class_name})
        quota_class = QUOTAS.get_class_quotas(context, id)
        return self._view_builder.detail_list(req, quota_class)

    def _validate_quota_limit(self, limit):
        # NOTE: -1 is a flag value for unlimited
        if limit < -1:
            msg = _("Quota limit must be -1 or greater.")
            raise exc.HTTPBadRequest(explanation=msg)


def create_resource():
    return wsgi.Resource(QuotaClassesController())
