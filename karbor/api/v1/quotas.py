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

"""The Quotas api."""

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from webob import exc

from karbor.api import common
from karbor.api.openstack import wsgi
from karbor.api.schemas import quotas as quota_schema
from karbor.api import validation
from karbor import db
from karbor import exception
from karbor.i18n import _
from karbor.policies import quotas as quota_policy

from karbor import quota


QUOTAS = quota.QUOTAS
NON_QUOTA_KEYS = ['tenant_id', 'id']
CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class QuotasViewBuilder(common.ViewBuilder):
    """Model a Quotas API response as a python dictionary."""

    _collection_name = "quota"

    def detail_list(self, request, quota, project_id=None):
        """Detailed view of a single quota."""
        keys = (
            'plans',
            'checkpoints',
        )
        view = {key: quota.get(key) for key in keys}
        if project_id:
            view['id'] = project_id
        return {self._collection_name: view}


class QuotasController(wsgi.Controller):
    """The Quotas API controller for the OpenStack API."""

    _view_builder_class = QuotasViewBuilder

    def __init__(self):
        super(QuotasController, self).__init__()

    def show(self, req, id):
        """Return data about the given quota id."""
        context = req.environ['karbor.context']
        LOG.info("Show quotas with id: %s", id, context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid project id provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        context.can(quota_policy.GET_POLICY)
        try:
            db.authorize_project_context(context, id)
            quota = self._get_quotas(context, id, usages=False)
        except exception.NotAuthorized:
            raise exc.HTTPForbidden()

        LOG.info("Show quotas request issued successfully.",
                 resource={'id': id})
        return self._view_builder.detail_list(req, quota, id)

    def detail(self, req, id):
        """Return data about the given quota."""
        context = req.environ['karbor.context']
        LOG.info("Show quotas detail with id: %s", id, context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid project id provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        context.can(quota_policy.GET_POLICY)
        try:
            db.authorize_project_context(context, id)
            quota = self._get_quotas(context, id, usages=True)
        except exception.NotAuthorized:
            raise exc.HTTPForbidden()

        LOG.info("Show quotas detail successfully.",
                 resource={'id': id})
        return self._view_builder.detail_list(req, quota, id)

    def defaults(self, req, id):
        """Return data about the given quotas."""
        context = req.environ['karbor.context']

        LOG.info("Show quotas defaults with id: %s", id,
                 context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid project id provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        context.can(quota_policy.GET_DEFAULT_POLICY)
        quotas = QUOTAS.get_defaults(context)

        LOG.info("Show quotas defaults successfully.",
                 resource={'id': id})
        return self._view_builder.detail_list(req, quotas, id)

    @validation.schema(quota_schema.update)
    def update(self, req, id, body):
        context = req.environ['karbor.context']

        LOG.info("Update quotas with id: %s", id,
                 context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid project id provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        context.can(quota_policy.UPDATE_POLICY)

        project_id = id
        bad_keys = []
        for key, value in body.get('quota', {}).items():
            if (key not in QUOTAS and key not in
                    NON_QUOTA_KEYS):
                bad_keys.append(key)
                continue
            if key not in NON_QUOTA_KEYS and value:
                try:
                    value = int(value)
                except (ValueError, TypeError):
                    msg = _("Quota '%(value)s' for %(key)s should be "
                            "integer.") % {'value': value, 'key': key}
                    LOG.warning(msg)
                    raise exc.HTTPBadRequest(explanation=msg)

        for key in body['quota'].keys():
            if key in QUOTAS:
                value = int(body['quota'][key])
                self._validate_quota_limit(value)
                try:
                    db.quota_update(context, project_id, key, value)
                except exception.ProjectQuotaNotFound:
                    db.quota_create(context, project_id, key, value)

        LOG.info("Update quotas successfully.",
                 resource={'id': project_id})
        return self._view_builder.detail_list(
            req, self._get_quotas(context, id))

    def _validate_quota_limit(self, limit):
        # NOTE: -1 is a flag value for unlimited
        if limit < -1:
            msg = _("Quota limit must be -1 or greater.")
            raise exc.HTTPBadRequest(explanation=msg)

    def _get_quotas(self, context, id, usages=False):
        values = QUOTAS.get_project_quotas(context, id, usages=usages)

        if usages:
            return values
        else:
            return dict((k, v['limit']) for k, v in values.items())

    def delete(self, req, id):
        context = req.environ['karbor.context']
        LOG.info("Delete quotas with id: %s", id,
                 context=context)

        if not uuidutils.is_uuid_like(id):
            msg = _("Invalid project id provided.")
            raise exc.HTTPBadRequest(explanation=msg)
        context.can(quota_policy.DELETE_POLICY)
        QUOTAS.destroy_all_by_project(context, id)

        LOG.info("Delete quotas successfully.",
                 resource={'id': id})


def create_resource():
    return wsgi.Resource(QuotasController())
