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

"""
OperationEngine Service
"""

from oslo_log import log as logging
import oslo_messaging as messaging

from karbor.common import constants
from karbor import context as karbor_context
from karbor import exception
from karbor import manager
from karbor import objects
from karbor.services.operationengine.engine.triggers import trigger_manager
from karbor.services.operationengine import user_trust_manager


LOG = logging.getLogger(__name__)


class OperationEngineManager(manager.Manager):
    """karbor OperationEngine Manager."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, service_name=None,
                 *args, **kwargs):
        super(OperationEngineManager, self).__init__(*args, **kwargs)
        self._service_id = None
        self._trigger_manager = None
        self._user_trust_manager = None

    def init_host(self, **kwargs):
        self._trigger_manager = trigger_manager.TriggerManager()
        self._service_id = kwargs.get("service_id")
        self._user_trust_manager = user_trust_manager.UserTrustManager()
        self._restore()

    def cleanup_host(self):
        self._trigger_manager.shutdown()

    def _restore(self):
        self._restore_triggers()
        self._restore_operations()

    def _restore_triggers(self):
        limit = 100
        marker = None
        filters = {}
        ctxt = karbor_context.get_admin_context()
        while True:
            triggers = objects.TriggerList.get_by_filters(
                ctxt, filters, limit, marker)
            if not triggers:
                break

            for trigger in triggers:
                self._trigger_manager.add_trigger(trigger.id, trigger.type,
                                                  trigger.properties)
            if len(triggers) < limit:
                break
            marker = triggers[-1].id

    def _restore_operations(self):
        limit = 100
        marker = None
        filters = {"service_id": self._service_id,
                   "state": [constants.OPERATION_STATE_REGISTERED,
                             constants.OPERATION_STATE_TRIGGERED,
                             constants.OPERATION_STATE_RUNNING]}
        columns_to_join = ['operation']
        ctxt = karbor_context.get_admin_context()
        resume_states = [constants.OPERATION_STATE_TRIGGERED,
                         constants.OPERATION_STATE_RUNNING]
        while True:
            states = objects.ScheduledOperationStateList.get_by_filters(
                ctxt, filters, limit, marker, columns_to_join=columns_to_join)
            if not states:
                break

            for state in states:
                operation = state.operation
                if not operation.enabled:
                    continue

                resume = (state.state in resume_states)
                self._trigger_manager.register_operation(
                    operation.trigger_id, operation.id,
                    resume=resume, end_time_for_run=state.end_time_for_run)

                self._user_trust_manager.resume_operation(
                    operation.id, operation.user_id,
                    operation.project_id, state.trust_id)
            if len(states) < limit:
                break
            marker = states[-1].id

    @messaging.expected_exceptions(exception.TriggerNotFound,
                                   exception.InvalidInput,
                                   exception.TriggerIsInvalid,
                                   exception.AuthorizationFailure,
                                   exception.ScheduledOperationExist)
    def create_scheduled_operation(self, context, operation_id, trigger_id):
        LOG.debug("Create scheduled operation.")

        # register operation
        self._trigger_manager.register_operation(trigger_id, operation_id)
        trust_id = self._user_trust_manager.add_operation(
            context, operation_id)

        # create ScheduledOperationState record
        state_info = {
            "operation_id": operation_id,
            "service_id": self._service_id,
            "trust_id": trust_id,
            "state": constants.OPERATION_STATE_REGISTERED
        }
        operation_state = objects.ScheduledOperationState(
            context, **state_info)
        try:
            operation_state.create()
        except Exception:
            self._trigger_manager.unregister_operation(
                trigger_id, operation_id)
            raise

    @messaging.expected_exceptions(exception.ScheduledOperationStateNotFound,
                                   exception.TriggerNotFound)
    def delete_scheduled_operation(self, context, operation_id, trigger_id):
        LOG.debug("Delete scheduled operation.")

        operation_state = objects.ScheduledOperationState.get_by_operation_id(
            context, operation_id)
        if constants.OPERATION_STATE_DELETED != operation_state.state:
            operation_state.state = constants.OPERATION_STATE_DELETED
            operation_state.save()

        self._trigger_manager.unregister_operation(trigger_id, operation_id)
        self._user_trust_manager.delete_operation(context, operation_id)

    @messaging.expected_exceptions(exception.TriggerNotFound)
    def suspend_scheduled_operation(self, context, operation_id, trigger_id):
        LOG.debug("Suspend scheduled operation.")
        self._trigger_manager.unregister_operation(trigger_id, operation_id)

    @messaging.expected_exceptions(exception.TriggerNotFound,
                                   exception.TriggerIsInvalid)
    def resume_scheduled_operation(self, context, operation_id, trigger_id):
        LOG.debug("Resume scheduled operation.")

        try:
            self._trigger_manager.register_operation(
                trigger_id, operation_id)
        except exception.ScheduledOperationExist:
            pass
        except Exception:
            raise

    @messaging.expected_exceptions(exception.InvalidInput)
    def create_trigger(self, context, trigger):
        self._trigger_manager.add_trigger(trigger.id, trigger.type,
                                          trigger.properties)

    @messaging.expected_exceptions(exception.TriggerNotFound,
                                   exception.DeleteTriggerNotAllowed)
    def delete_trigger(self, context, trigger_id):
        self._trigger_manager.remove_trigger(trigger_id)

    @messaging.expected_exceptions(exception.TriggerNotFound,
                                   exception.InvalidInput)
    def update_trigger(self, context, trigger):
        self._trigger_manager.update_trigger(trigger.id, trigger.properties)
