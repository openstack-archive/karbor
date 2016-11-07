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

from abc import ABCMeta
from abc import abstractmethod
import six

from karbor import loadables


@six.add_metaclass(ABCMeta)
class BaseTrigger(object):
    """Trigger base class that all Triggers should inherit from"""

    TRIGGER_TYPE = ""

    def __init__(self, trigger_id, trigger_property, executor):
        super(BaseTrigger, self).__init__()

        self._id = trigger_id
        self._operation_ids = set()
        self._executor = executor

    @abstractmethod
    def shutdown(self):
        pass

    @abstractmethod
    def register_operation(self, operation_id, **kwargs):
        pass

    @abstractmethod
    def unregister_operation(self, operation_id, **kwargs):
        pass

    @abstractmethod
    def update_trigger_property(self, trigger_property):
        pass

    @classmethod
    @abstractmethod
    def check_trigger_definition(cls, trigger_definition):
        pass

    @classmethod
    @abstractmethod
    def check_configuration(cls):
        pass

    def has_operations(self):
        return (len(self._operation_ids) != 0)


class TriggerHandler(loadables.BaseLoader):

    def __init__(self):
        super(TriggerHandler, self).__init__(BaseTrigger)


def all_triggers():
    """Get all trigger classes."""
    return TriggerHandler().get_all_classes()
