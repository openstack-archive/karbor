# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from karbor.common import constants
from karbor.services.protection.graph import build_graph
from karbor.services.protection.protectable_registry import ProtectableRegistry
from karbor.services.protection.provider import ProviderRegistry

from karbor.tests import base
from karbor.tests.unit.protection.fakes import fake_protection_plan
from karbor.tests.unit.protection.fakes import fake_restore
from karbor.tests.unit.protection.fakes import FakeCheckpoint
from karbor.tests.unit.protection.fakes import FakeProtectionPlugin
from karbor.tests.unit.protection.fakes import plan_resources
from karbor.tests.unit.protection.fakes import resource_map


class FakeWorkflowEngine(object):
    def build_flow(self, flow_name):
        self.flow_name = flow_name
        self.task_flow = []
        return self.task_flow

    def add_tasks(self, task_flow, task):
        task_flow.append(task)

    def create_task(self, func, **kwargs):
        return "fake_task"


class FakeProtectableRegistry(object):
    def fetch_dependent_resources(self, resource):
        return resource_map.__getitem__(resource)

    def build_graph(self, context, resources):
        return build_graph(
            start_nodes=resources,
            get_child_nodes_func=self.fetch_dependent_resources,
        )


class PluggableProtectionProviderTest(base.TestCase):
    def setUp(self):
        super(PluggableProtectionProviderTest, self).setUp()

    @mock.patch.object(ProtectableRegistry, 'build_graph')
    def test_build_protect_task_flow(self, mock_build_graph):
        pr = ProviderRegistry()
        self.assertEqual(len(pr.providers), 1)

        plugable_provider = pr.providers["fake_id1"]
        cntxt = "fake_cntxt"
        plan = fake_protection_plan()
        workflow_engine = FakeWorkflowEngine()
        operation = constants.OPERATION_PROTECT

        ctx = {"context": cntxt,
               "plan": plan,
               "workflow_engine": workflow_engine,
               "operation_type": operation,
               }

        expected_calls = [
            ("on_resource_start", 'A', True),
            ("on_resource_start", 'C', True),
            ("on_resource_start", 'D', True),
            ("on_resource_end", 'D'),
            ("on_resource_start", 'E', True),
            ("on_resource_end", 'E'),
            ("on_resource_end", 'C'),
            ("on_resource_end", 'A'),
            ("on_resource_start", 'B', True),
            ("on_resource_start", 'C', False),
            ("on_resource_start", 'D', False),
            ("on_resource_end", 'D'),
            ("on_resource_start", 'E', False),
            ("on_resource_end", 'E'),
            ("on_resource_end", 'C'),
            ("on_resource_end", 'B'),
        ]

        fake_registry = FakeProtectableRegistry()
        plugable_provider.protectable_registry = fake_registry

        fake_registry.build_graph = mock.MagicMock()
        resource_graph = build_graph(plan_resources, resource_map.__getitem__)
        mock_build_graph.return_value = resource_graph

        fake_protection_plugin = FakeProtectionPlugin(expected_calls)
        plugable_provider._plugin_map = {
            "fake_plugin": fake_protection_plugin
        }

        result = plugable_provider.build_task_flow(ctx)
        self.assertEqual(len(result["status_getters"]), 5)
        self.assertEqual(len(result["task_flow"]), 5)

    def test_build_restore_task_flow(self):
        pr = ProviderRegistry()
        self.assertEqual(len(pr.providers), 1)

        plugable_provider = pr.providers["fake_id1"]
        cntxt = "fake_cntxt"
        restore = fake_restore()
        checkpoint = FakeCheckpoint()
        workflow_engine = FakeWorkflowEngine()
        operation = constants.OPERATION_RESTORE

        ctx = {"context": cntxt,
               "restore": restore,
               "workflow_engine": workflow_engine,
               "operation_type": operation,
               "checkpoint": checkpoint,
               "heat_template": "heat_template"
               }

        expected_calls = [
            ("on_resource_start", 'A', True),
            ("on_resource_start", 'C', True),
            ("on_resource_start", 'D', True),
            ("on_resource_end", 'D'),
            ("on_resource_start", 'E', True),
            ("on_resource_end", 'E'),
            ("on_resource_end", 'C'),
            ("on_resource_end", 'A'),
            ("on_resource_start", 'B', True),
            ("on_resource_start", 'C', False),
            ("on_resource_start", 'D', False),
            ("on_resource_end", 'D'),
            ("on_resource_start", 'E', False),
            ("on_resource_end", 'E'),
            ("on_resource_end", 'C'),
            ("on_resource_end", 'B'),
        ]

        fake_protection_plugin = FakeProtectionPlugin(expected_calls)
        plugable_provider._plugin_map = {
            "fake_plugin": fake_protection_plugin
        }

        result = plugable_provider.build_task_flow(ctx)
        self.assertEqual(len(result["task_flow"]), 5)

    def tearDown(self):
        super(PluggableProtectionProviderTest, self).tearDown()
