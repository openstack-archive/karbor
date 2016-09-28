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

import abc
import six

from karbor.common import constants
from karbor.services.protection.protection_plugin import ProtectionPlugin


@six.add_metaclass(abc.ABCMeta)
class BaseProtectionPlugin(ProtectionPlugin):
    def __init__(self, config=None):
        super(BaseProtectionPlugin, self).__init__(config)
        # operation == "start" or "suspend" not support
        self.task_callback_map = {
            constants.OPERATION_PROTECT: self.create_backup,
            constants.OPERATION_RESTORE: self.restore_backup,
            constants.OPERATION_DELETE: self.delete_backup
        }

    @abc.abstractmethod
    def create_backup(self, cntxt, checkpoint, **kwargs):
        pass

    @abc.abstractmethod
    def restore_backup(self, cntxt, checkpoint, **kwargs):
        pass

    @abc.abstractmethod
    def delete_backup(self, cntxt, checkpoint, **kwargs):
        pass

    def on_resource_start(self, context):
        task = None
        kwargs = {}
        inject = {}
        requires = []
        parameters = {}
        resource = context.node.value
        if context.is_first_visited is True:
            parameters['node'] = context.node
            parameters['cntxt'] = context.cntxt
            kwargs['name'] = resource.id
            operation = context.operation
            if operation == constants.OPERATION_PROTECT:
                parameters.update(context.parameters.get(resource.type, {}))
                res_params = resource.type + '#' + str(resource.id)
                parameters.update(context.parameters.get(res_params, {}))
                inject = parameters
                requires = parameters.keys()
                requires.append('checkpoint')
            elif operation == constants.OPERATION_RESTORE:
                parameters.update(context.parameters.get(resource.type, {}))
                res_params = resource.type + '#' + str(resource.id)
                parameters.update(context.parameters.get(res_params, {}))
                parameters['checkpoint'] = context.checkpoint
                parameters['heat_template'] = context.heat_template
                inject = parameters
                requires = parameters.keys()
            elif operation == constants.OPERATION_DELETE:
                parameters['checkpoint'] = context.checkpoint
                inject = parameters
                requires = parameters.keys()
                requires.append('checkpoint')

            task_callback = self.task_callback_map.get(operation, None)
            if task_callback is not None:
                task = context.workflow_engine.create_task(task_callback,
                                                           inject=inject,
                                                           requires=requires,
                                                           **kwargs)
                context.workflow_engine.add_tasks(context.task_flow, task)
        else:
            task = context.workflow_engine.search_task(context.task_flow,
                                                       resource.id)
        if task is not None:
            context.task_stack.append(task)

    def on_resource_end(self, context):
        operation = context.operation
        task_stack = context.task_stack
        if operation in self.task_callback_map:
            length = len(task_stack)
            if length > 1:
                child_task = task_stack.pop()
                parent_task = task_stack[-1]
                context.workflow_engine.link_task(context.task_flow,
                                                  child_task, parent_task)
            else:
                task_stack.pop()

    def get_resource_stats(self, checkpoint, resource_id):
        # Get the status of this resource
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        try:
            status = bank_section.get_object("status")
            return status
        except Exception:
            return constants.RESOURCE_STATUS_UNDEFINED
