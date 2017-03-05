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
Manage all triggers.
"""

from karbor import exception
from karbor.i18n import _
from karbor.services.operationengine.engine import triggers as all_triggers


class TriggerManager(object):
    """Manage all trigger classes which are defined at triggers dir."""

    def __init__(self, executor):
        super(TriggerManager, self).__init__()

        all_cls = all_triggers.all_triggers()
        self._trigger_cls_map = {cls.TRIGGER_TYPE:
                                 cls for cls in all_cls}

        for t, cls in self._trigger_cls_map.items():
            cls.check_configuration()

        # self._trigger_obj_map = {
        #     trigger_id: trigger,
        # }
        self._trigger_obj_map = {}

        self._executor = executor

    def shutdown(self):

        for trigger_id, trigger in self._trigger_obj_map.items():
            trigger.shutdown()

        self._trigger_obj_map.clear()
        self._trigger_cls_map.clear()

        if self._executor:
            self._executor.shutdown()
            self._executor = None

    def check_trigger_definition(self, trigger_type, trigger_definition):
        """Check trigger definition

        :param trigger_type: Type of trigger
        :param trigger_definition: Definition of trigger
        """

        trigger_cls = self._get_trigger_class(trigger_type)
        trigger_cls.check_trigger_definition(trigger_definition)

    def add_trigger(self, trigger_id, trigger_type, trigger_property):
        if trigger_id in self._trigger_obj_map:
            msg = (_("Trigger id(%s) is exist") % trigger_id)
            raise exception.InvalidInput(msg)

        trigger_cls = self._get_trigger_class(trigger_type)
        trigger = trigger_cls(trigger_id, trigger_property, self._executor)
        self._trigger_obj_map[trigger_id] = trigger

    def remove_trigger(self, trigger_id):
        trigger = self._trigger_obj_map.get(trigger_id, None)
        if not trigger:
            raise exception.TriggerNotFound(id=trigger_id)

        if trigger.has_operations():
            raise exception.DeleteTriggerNotAllowed(trigger_id=trigger_id)

        trigger.shutdown()
        del self._trigger_obj_map[trigger_id]

    def update_trigger(self, trigger_id, trigger_property):
        trigger = self._trigger_obj_map.get(trigger_id, None)
        if not trigger:
            raise exception.TriggerNotFound(id=trigger_id)

        trigger.update_trigger_property(trigger_property)

    def register_operation(self, trigger_id, operation_id, **kwargs):
        """Register operation definition.

        :param trigger_id: The ID of the trigger which
                           the operation is registered to
        :param operation_id: ID of the operation
        :param kwargs: Any parameters
        :raise InvalidInput if the trigger_type is invalid or
               other exceptionis register_operation of trigger raises
        """
        trigger = self._trigger_obj_map.get(trigger_id, None)
        if not trigger:
            raise exception.TriggerNotFound(id=trigger_id)

        trigger.register_operation(operation_id, **kwargs)

        if kwargs.get('resume'):
            self._executor.resume_operation(operation_id, **kwargs)

    def unregister_operation(self, trigger_id, operation_id, **kwargs):
        """Unregister operation.

        :param trigger_id: The ID of the trigger which
                           the operation is registered to
        :param operation_id: ID of the operation
        :raise InvalidInput if the trigger_type is invalid or
               other exceptionis unregister_operation of trigger raises
        """
        trigger = self._trigger_obj_map.get(trigger_id, None)
        if not trigger:
            raise exception.TriggerNotFound(id=trigger_id)

        trigger.unregister_operation(operation_id, **kwargs)
        self._executor.cancel_operation(operation_id)

    def _get_trigger_class(self, trigger_type):
        cls = self._trigger_cls_map.get(trigger_type, None)
        if not cls:
            msg = (_("Invalid trigger type:%s") % trigger_type)
            raise exception.InvalidInput(msg)

        return cls
