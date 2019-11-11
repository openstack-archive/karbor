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

from oslo_log import log as logging
from oslo_utils import uuidutils

from karbor.common import constants
from karbor import context
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.services.operationengine.operations import base

LOG = logging.getLogger(__name__)


class ProtectOperation(base.Operation):
    """Protect operation."""

    OPERATION_TYPE = "protect"

    def check_operation_definition(self, operation_definition):
        provider_id = operation_definition.get("provider_id")
        if not provider_id or not uuidutils.is_uuid_like(provider_id):
            reason = _("Provider_id is invalid")
            raise exception.InvalidOperationDefinition(reason=reason)

        plan_id = operation_definition.get("plan_id")
        if not plan_id or not uuidutils.is_uuid_like(plan_id):
            reason = _("Plan_id is invalid")
            raise exception.InvalidOperationDefinition(reason=reason)

        plan = objects.Plan.get_by_id(context.get_admin_context(), plan_id)
        if provider_id != plan.provider_id:
            reason = _("Provider_id is conflict")
            raise exception.InvalidOperationDefinition(reason=reason)

    def _execute(self, operation_definition, param):
        LOG.debug("_execute operation starting")
        log_ref = self._create_operation_log(param)
        self._run(operation_definition, param, log_ref)

    def _resume(self, operation_definition, param, log_ref):
        LOG.debug("_resume operation starting")
        self._run(operation_definition, param, log_ref)

    def _run(self, operation_definition, param, log_ref):
        client = self._create_karbor_client(
            param.get("user_id"), param.get("project_id"))
        provider_id = operation_definition.get("provider_id")
        plan_id = operation_definition.get("plan_id")
        trigger_id = param.get("trigger_id", None)
        scheduled_operation_id = param.get("scheduled_operation_id", None)
        extra_info = {
            'created_by': constants.OPERATION_ENGINE,
            'trigger_id': trigger_id,
            'scheduled_operation_id': scheduled_operation_id
        }
        LOG.debug("Create checkpoint: provider_id=%(provider_id)s, "
                  "plan_id=%(plan_id)s, trigger_id=%(trigger_id)s, "
                  "scheduled_operation_id=%(scheduled_operation_id)s" %
                  {"provider_id": provider_id,
                   "plan_id": plan_id,
                   "trigger_id": trigger_id,
                   "scheduled_operation_id": scheduled_operation_id})
        try:
            client.checkpoints.create(provider_id, plan_id, extra_info)
        except Exception:
            state = constants.OPERATION_EXE_STATE_FAILED
        else:
            state = constants.OPERATION_EXE_STATE_SUCCESS

        LOG.debug("Create checkpoint finished, state=%s" % state)
        self._update_log_when_operation_finished(log_ref, state)
