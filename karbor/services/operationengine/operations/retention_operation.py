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

from datetime import datetime
from oslo_log import log as logging
from oslo_utils import uuidutils

from karbor.common import constants
from karbor import context
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.services.operationengine.operations import base

LOG = logging.getLogger(__name__)


class RetentionProtectOperation(base.Operation):
    """Protect operation."""

    OPERATION_TYPE = "retention_protect"

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
        project_id = param.get("project_id")
        client = self._create_karbor_client(
            param.get("user_id"), project_id)
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

        finally:
            LOG.debug("Create checkpoint finished, state=%s" % state)
            self._update_log_when_operation_finished(log_ref, state)

        try:
            max_backups = int(operation_definition.get("max_backups", -1))
            max_backups = -1 if max_backups <= 0 else max_backups
        except Exception:
            state = constants.OPERATION_GET_MAX_BACKUP_STATE_FAILED
            self._update_log_when_operation_finished(log_ref, state)
            reason = _("Failed to get max_backups")
            raise exception.InvalidOperationDefinition(reason=reason)

        try:
            retention_duration = int(operation_definition.get(
                "retention_duration", -1))
            retention_duration = -1 if retention_duration <= 0\
                else retention_duration
        except Exception:
            state = constants.OPERATION_GET_DURATION_STATE_FAILED
            self._update_log_when_operation_finished(log_ref, state)
            reason = _("Failed to get retention_duration")
            raise exception.InvalidOperationDefinition(reason=reason)

        try:
            self._delete_old_backup_by_max_backups(
                client, max_backups, project_id, provider_id, plan_id)
            state = constants.OPERATION_EXE_MAX_BACKUP_STATE_SUCCESS
        except Exception:
            state = constants.OPERATION_EXE_MAX_BACKUP_STATE_FAILED
            reason = (_("Can't execute retention policy provider_id: "
                        "%(provider_id)s plan_id:%(plan_id)s"
                        " max_backups:%(max_backups)s") %
                      {"provider_id": provider_id, "plan_id": plan_id,
                       "max_backups": max_backups})
            raise exception.InvalidOperationDefinition(reason=reason)
        finally:
            LOG.debug("Delete old backup by max_backups finished, "
                      "state=%(state)s, max_backups:%(max_backups)s" %
                      {"state": state, "max_backups": max_backups})
            self._update_log_when_operation_finished(log_ref, state)

        try:
            self._delete_old_backup_by_duration(
                client, retention_duration, project_id, provider_id, plan_id)
            state = constants.OPERATION_EXE_DURATION_STATE_SUCCESS
        except Exception:
            state = constants.OPERATION_EXE_DURATION_STATE_FAILED
            reason = (_("Can't execute retention policy provider_id: "
                        "%(provider_id)s plan_id:%(plan_id)s"
                        " retention_duration:%(retention_duration)s") %
                      {"provider_id": provider_id, "plan_id": plan_id,
                       "retention_duration": retention_duration})
            raise exception.InvalidOperationDefinition(reason=reason)
        finally:
            LOG.debug("Delete old backup by duration finished, "
                      "state=%(state)s, "
                      "retention_duration:%(retention_duration)s" %
                      {"state": state,
                       "retention_duration": retention_duration})
            self._update_log_when_operation_finished(log_ref, state)

    @staticmethod
    def _list_available_checkpoint(client, project_id,
                                   provider_id, plan_id):
        search_opts = {'project_id': project_id,
                       'plan_id': plan_id,
                       "status": constants.CHECKPOINT_STATUS_AVAILABLE
                       }
        sort = {"created_at": "desc"}
        try:
            checkpoints = client.checkpoints.list(
                provider_id=provider_id,
                search_opts=search_opts,
                limit=None,
                sort=sort)
            avi_check = [x for x in checkpoints if x.status ==
                         constants.CHECKPOINT_STATUS_AVAILABLE]
        except Exception as e:
            reason = (_("Failed to list checkpoint by %(provider_id)s"
                        "and %(plan_id)s reason: %(reason)s") %
                      {"provider_id": provider_id,
                       "plan_id": plan_id, "reason": e})
            raise exception.InvalidOperationDefinition(reason=reason)

        return avi_check

    def _delete_old_backup_by_max_backups(
            self, client, max_backups, project_id, provider_id, plan_id):

        if max_backups == -1:
            return

        backup_items = self._list_available_checkpoint(
            client, project_id, provider_id, plan_id)

        LOG.debug("Delete checkpoint: max_backups=%(max_backups)s, "
                  "project_id=%(project_id)s, provider_id=%(provider_id)s, "
                  "plan_id=%(plan_id)s" %
                  {"max_backups": max_backups,
                   "project_id": project_id,
                   "provider_id": provider_id,
                   "plan_id": plan_id})
        count = len(backup_items)
        if count > max_backups:
            for item in backup_items[max_backups:]:
                try:
                    client.checkpoints.delete(provider_id, item.id)
                except Exception as e:
                    reason = (_("Failed to delete checkpoint: %(cp_id)s by "
                                "max_backups with the reason: %(reason)s") %
                              {"cp_id": item.id, "reason": e})
                    raise exception.InvalidOperationDefinition(reason=reason)

    def _delete_old_backup_by_duration(
            self, client, retention_duration,
            project_id, provider_id, plan_id):

        if retention_duration == -1:
            return

        backup_items = self._list_available_checkpoint(
            client, project_id, provider_id, plan_id)

        LOG.debug("Delete checkpoint: "
                  "retention_duration=%(retention_duration)s, "
                  "project_id=%(project_id)s, provider_id=%(provider_id)s, "
                  "plan_id=%(plan_id)s" %
                  {"retention_duration": retention_duration,
                   "project_id": project_id,
                   "provider_id": provider_id,
                   "plan_id": plan_id})
        now = datetime.utcnow()
        for item in backup_items:
            created_at = datetime.strptime(item.created_at, "%Y-%m-%d")
            interval = (now - created_at).days
            if interval > retention_duration:
                try:
                    client.checkpoints.delete(provider_id, item.id)
                except Exception as e:
                    reason = (_("Failed to delete checkpoint: %(cp_id)s "
                                "by retention_duration with the reasion: "
                                "%(reason)s") %
                              {"cp_id": item.id, "reason": e})
                    raise exception.InvalidOperationDefinition(reason=reason)
