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

import mock
from stevedore import extension as import_driver

from karbor import exception
from karbor.services.operationengine.engine.executors import base as base_exe
from karbor.services.operationengine.engine import triggers
from karbor.services.operationengine.engine.triggers import trigger_manager
from karbor.tests import base


class FakeTrigger(triggers.BaseTrigger):
    def __init__(self, trigger_id, trigger_property, executor):
        super(FakeTrigger, self).__init__(trigger_id, trigger_property,
                                          executor)
        self._ops = set()

    def shutdown(self):
        pass

    def register_operation(self, operation_id, **kwargs):
        self._ops.add(operation_id)

    def unregister_operation(self, operation_id, **kwargs):
        self._ops.discard(operation_id)

    def update_trigger_property(self, trigger_property):
        pass

    @classmethod
    def check_trigger_definition(cls, trigger_definition):
        pass

    @classmethod
    def check_configuration(cls):
        pass

    def has_operations(self):
        return bool(self._ops)


class FakeExecutor(base_exe.BaseExecutor):
    def execute_operation(self, operation_id, triggered_time,
                          expect_start_time, window_time, **kwargs):
        pass

    def resume_operation(self, operation_id, **kwargs):
        pass

    def cancel_operation(self, operation_id):
        pass

    def shutdown(self):
        pass

    @classmethod
    def obj(cls):
        return cls

    @classmethod
    def name(cls):
        return "FakeExecutor"


class TriggerManagerTestCase(base.TestCase):

    def setUp(self):
        super(TriggerManagerTestCase, self).setUp()

        with mock.patch.object(import_driver.ExtensionManager,
                               '_load_plugins') as load_plugin:
            load_plugin.return_value = [FakeExecutor]

            self._executor = FakeExecutor(None)
            self._manager = trigger_manager.TriggerManager(self._executor)
            self._trigger_type = 'fake'
            self._manager._trigger_cls_map[self._trigger_type] = FakeTrigger

    def tearDown(self):
        self._manager.shutdown()
        super(TriggerManagerTestCase, self).tearDown()

    @mock.patch.object(FakeTrigger, 'check_trigger_definition')
    def test_check_trigger_definition(self, func):
        self._manager.check_trigger_definition(self._trigger_type, {})
        func.assert_called_once_with({})

    def test_add_trigger(self):
        trigger_id = 'add'
        self._add_a_trigger(trigger_id)
        self.assertRaisesRegex(exception.InvalidInput,
                               'Trigger id.* is exist',
                               self._manager.add_trigger,
                               trigger_id, self._trigger_type, {})

        self.assertRaisesRegex(exception.InvalidInput,
                               'Invalid trigger type.*',
                               self._manager.add_trigger,
                               1, 'abc', {})

    def test_remove_trigger(self):
        self.assertRaises(exception.TriggerNotFound,
                          self._manager.remove_trigger,
                          1)
        trigger_id = 'remove'
        op_id = 1
        self._add_a_trigger(trigger_id)
        self._manager.register_operation(trigger_id, op_id)

        self.assertRaises(exception.DeleteTriggerNotAllowed,
                          self._manager.remove_trigger,
                          trigger_id)

        self._manager.unregister_operation(trigger_id, op_id)
        self._manager.remove_trigger(trigger_id)
        self.assertRaises(exception.TriggerNotFound,
                          self._manager.remove_trigger,
                          trigger_id)

    @mock.patch.object(FakeTrigger, 'update_trigger_property')
    def test_update_trigger(self, func):
        self.assertRaises(exception.TriggerNotFound,
                          self._manager.update_trigger,
                          1, {})

        trigger_id = 'update'
        self._add_a_trigger(trigger_id)
        self._manager.update_trigger(trigger_id, {})
        func.assert_called_once_with({})

    @mock.patch.object(FakeTrigger, 'register_operation')
    @mock.patch.object(FakeExecutor, 'resume_operation')
    def test_register_operation(self, resume, register):
        self.assertRaises(exception.TriggerNotFound,
                          self._manager.register_operation,
                          1, 1)
        trigger_id = 'register'
        self._add_a_trigger(trigger_id)
        op_id = 1
        self._manager.register_operation(trigger_id, op_id, resume=1)
        register.assert_called_once_with(op_id, resume=1)
        resume.assert_called_once_with(op_id, resume=1)

    @mock.patch.object(FakeTrigger, 'unregister_operation')
    @mock.patch.object(FakeExecutor, 'cancel_operation')
    def test_unregister_operation(self, cancel, unregister):
        self.assertRaises(exception.TriggerNotFound,
                          self._manager.unregister_operation,
                          1, 1)
        trigger_id = 'unregister'
        self._add_a_trigger(trigger_id)
        op_id = 1
        self._manager.unregister_operation(trigger_id, op_id)
        unregister.assert_called_once_with(op_id)
        cancel.assert_called_once_with(op_id)

    def _add_a_trigger(self, trigger_id):
        self._manager.add_trigger(trigger_id, self._trigger_type, {})
