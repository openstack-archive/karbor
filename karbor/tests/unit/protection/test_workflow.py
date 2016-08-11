# Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from karbor.services.protection.flows import workflow
from karbor.tests import base


def fake_func():
    return True


class WorkFlowTest(base.TestCase):
    def setUp(self):
        super(WorkFlowTest, self).setUp()
        self.workflow_engine = workflow.TaskFlowEngine()

    def test_create_task(self):
        test_task = self.workflow_engine.create_task(fake_func, name='fake')
        self.assertEqual('fake', test_task.name)

    def test_add_task(self):
        test_flow = self.workflow_engine.build_flow('test')
        test_task = self.workflow_engine.create_task(fake_func, name='fake')
        self.workflow_engine.add_tasks(test_flow, test_task)
        self.assertEqual(1, len(test_flow))

    def test_search_task(self):
        flow = self.workflow_engine.build_flow('test')
        task1 = self.workflow_engine.create_task(fake_func, name='fake_func')
        task2 = self.workflow_engine.create_task(fake_func, name='fake_func2')
        self.workflow_engine.add_tasks(flow, task1, task2)
        result = self.workflow_engine.search_task(flow, 'fake_func2')
        self.assertEqual('fake_func2', getattr(result, 'name'))
