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

from karbor.resource import Resource
from karbor.services.protection.protectable_plugin import ProtectablePlugin
from karbor.services.protection.protectable_registry import ProtectableRegistry

from karbor.tests import base

_FAKE_TYPE = "Karbor::Test::Fake"


class _FakeProtectablePlugin(ProtectablePlugin):
    def __init__(self, cntx):
        super(_FakeProtectablePlugin, self).__init__(cntx)
        self.graph = {}

    def instance(self, cntx):
        new = self.__class__(cntx)
        new.graph = self.graph
        return new

    def get_resource_type(self):
        return _FAKE_TYPE

    def get_parent_resource_types(self):
        return _FAKE_TYPE

    def list_resources(self, context):
        return self.graph.values()

    def show_resource(self, context, resource_id):
        return [Resource(type=_FAKE_TYPE,
                         id=resource.id,
                         name=resource.name)
                for resource in self.graph
                if resource.id == resource_id]

    def get_dependent_resources(self, context, parent_resource):
        return self.graph[parent_resource]


class ProtectableRegistryTest(base.TestCase):
    def setUp(self):
        super(ProtectableRegistryTest, self).setUp()
        self.protectable_registry = ProtectableRegistry()
        self._fake_plugin = _FakeProtectablePlugin(None)
        self.protectable_registry.register_plugin(self._fake_plugin)

    def test_graph_building(self):
        A = Resource(_FAKE_TYPE, "A", 'nameA')
        B = Resource(_FAKE_TYPE, "B", 'nameB')
        C = Resource(_FAKE_TYPE, "C", 'nameC')
        test_matrix = (
            (
                {A: [B],
                 B: [C],
                 C: []},
                (A, C)
            ),
            (
                {A: [C],
                 B: [C],
                 C: []},
                (A, C)
            ),
        )

        for g, resources in test_matrix:
            self._fake_plugin.graph = g
            result_graph = self.protectable_registry.build_graph(None,
                                                                 resources)
            self.assert_graph(result_graph, g)
            self.protectable_registry._protectable_map = {}

    def assert_graph(self, g, g_dict):
        for item in g:
            expected = set(g_dict[item.value])
            found = set(child.value for child in item.child_nodes)
            self.assertEqual(found, expected)
            self.assert_graph(item.child_nodes, g_dict)
