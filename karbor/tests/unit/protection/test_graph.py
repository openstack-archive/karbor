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
from collections import namedtuple
from oslo_serialization import jsonutils
from oslo_serialization import msgpackutils

from karbor import exception
from karbor import resource
import karbor.services.protection.graph as graph
from karbor.tests import base


class GraphBuilderTest(base.TestCase):
    def test_source_set(self):
        """Test that the source set only contains sources"""

        test_matrix = (
            ({
                "A": ["B"],
                "B": ["C"],
                "C": [],
                }, {"A"}),
            ({
                "A": [],
                "B": ["C"],
                "C": [],
                }, {"A", "B"}),
            ({
                "A": ["C"],
                "B": ["C"],
                "C": [],
                }, {"A", "B"}),
        )

        for g, expected_result in test_matrix:
            result = graph.build_graph(g.keys(), g.__getitem__)
            self.assertEqual({node.value for node in result}, expected_result)

    def test_detect_cyclic_graph(self):
        """Test that cyclic graphs are detected"""

        test_matrix = (
            ({
                "A": ["B"],
                "B": ["C"],
                "C": [],
                }, False),
            ({
                "A": [],
                "B": ["C"],
                "C": [],
                }, False),
            ({
                "A": ["C"],
                "B": ["C"],
                "C": ["A"],
                }, True),
            ({
                "A": ["B"],
                "B": ["C"],
                "C": ["A"],
                }, True),
        )

        for g, expected_result in test_matrix:
            if expected_result:
                self.assertRaises(
                    graph.FoundLoopError,
                    graph.build_graph,
                    g.keys(), g.__getitem__,
                )
            else:
                graph.build_graph(g.keys(), g.__getitem__)

    def test_diamond_graph(self):
        def test_node_children(testnode):
            return testnode.children

        TestNode = namedtuple('TestNode', ['id', 'children'])
#          A
#         / \
#        B   C
#         \ /
#          D
        test_diamond_left = TestNode('D', ())
        test_diamond_right = TestNode('D', ())
        print('id left: ', id(test_diamond_left))
        print('id right:', id(test_diamond_right))
        test_left = TestNode('B', (test_diamond_left, ))
        test_right = TestNode('C', (test_diamond_right, ))
        test_root = TestNode('A', (test_left, test_right, ))
        test_nodes = {test_root, }
        result_graph = graph.build_graph(test_nodes, test_node_children)
        test_root_node = result_graph[0]
        self.assertEqual(len(test_root_node.child_nodes), 2)
        test_left_node = test_root_node.child_nodes[0]
        test_right_node = test_root_node.child_nodes[1]

        self.assertEqual(id(test_left_node.child_nodes[0]),
                         id(test_right_node.child_nodes[0]))

    def test_graph_pack_unpack(self):
        test_base = {
            "A1": ["B1", "B2"],
            "B1": ["C1", "C2"],
            "B2": ["C3", "C2"],
            "C1": [],
            "C2": [],
            "C3": [],
        }

        test_graph = graph.build_graph(test_base.keys(), test_base.__getitem__)
        packed_graph = graph.pack_graph(test_graph)
        unpacked_graph = graph.unpack_graph(packed_graph)
        self.assertEqual(test_graph, unpacked_graph)

    def test_graph_serialize_deserialize(self):
        Format = namedtuple('Format', ['loads', 'dumps'])
        formats = [
            Format(jsonutils.loads, jsonutils.dumps),
            Format(msgpackutils.loads, msgpackutils.dumps),
        ]
        test_base = {
            "A1": ["B1", "B2"],
            "B1": ["C1", "C2"],
            "B2": ["C3", "C2"],
            "C1": [],
            "C2": [],
            "C3": [],
        }

        test_graph = graph.build_graph(test_base.keys(), test_base.__getitem__)
        for fmt in formats:
            serialized = fmt.dumps(graph.pack_graph(test_graph))
            unserialized = graph.unpack_graph(fmt.loads(serialized))
            self.assertEqual(test_graph, unserialized)

    def test_graph_serialize(self):
        resource_a = resource.Resource('server', 0, 'a', {'name': 'a'})
        resource_b = resource.Resource('volume', 1, 'b', {'name': 'b'})
        test_base = {
            resource_a: [resource_b],
            resource_b: []
        }
        test_graph = graph.build_graph(test_base.keys(), test_base.__getitem__)
        self.assertIn(
            graph.serialize_resource_graph(test_graph),
            [
                '[{"0x1": ["server", 0, "a", {"name": "a"}], '
                '"0x0": ["volume", 1, "b", {"name": "b"}]}, '
                '[["0x1", ["0x0"]]]]',
                '[{"0x0": ["volume", 1, "b", {"name": "b"}], '
                '"0x1": ["server", 0, "a", {"name": "a"}]}, '
                '[["0x1", ["0x0"]]]]'
            ])

    def test_graph_deserialize_unordered_adjacency(self):
        test_base = {
            "A1": ["B1", "B2"],
            "B1": ["C1", "C2"],
            "B2": ["C3", "C2"],
            "C1": [],
            "C2": [],
            "C3": [],
        }
        test_graph = graph.build_graph(test_base.keys(), test_base.__getitem__)
        packed_graph = graph.pack_graph(test_graph)
        reversed_adjacency = tuple(reversed(packed_graph.adjacency))
        packed_graph = graph.PackedGraph(packed_graph.nodes,
                                         reversed_adjacency)
        with self.assertRaisesRegex(exception.InvalidInput, "adjacency list"):
            graph.unpack_graph(packed_graph)

    def test_pack_unpack_graph_with_isolated_node(self):
        test_base = {
            "A1": ["B1", "B2"],
            "B1": ["C1", "C2"],
            "B2": ["C3", "C2"],
            "C1": [],
            "C2": [],
            "C3": [],
            "C4": []
        }

        test_graph = graph.build_graph(test_base.keys(), test_base.__getitem__)
        packed_graph = graph.pack_graph(test_graph)
        unpacked_graph = graph.unpack_graph(packed_graph)
        self.assertEqual(len(test_graph), len(unpacked_graph))
        for start_node in test_graph:
            self.assertIn(start_node, unpacked_graph)

    def test_pack_unpack_graph(self):
        test_base = {
            "A1": ["B1", "B2", "B3", "B4"],
            "B1": [],
            "B2": [],
            "B3": ["B1"],
            "B4": ["B2"],
        }

        test_graph = graph.build_graph(test_base.keys(), test_base.__getitem__)
        packed_graph = graph.pack_graph(test_graph)
        unpacked_graph = graph.unpack_graph(packed_graph)
        self.assertEqual(len(test_graph), len(unpacked_graph))
        for start_node in test_graph:
            self.assertIn(start_node, unpacked_graph)


class _TestGraphWalkerListener(graph.GraphWalkerListener):
    def __init__(self, expected_event_stream, test):
        super(_TestGraphWalkerListener, self).__init__()
        # Because the testing framework is badly designed
        # I need to have a reference to the test to raise assertions
        self._test = test
        self._expected_expected_event_stream = list(expected_event_stream)

    def on_node_enter(self, node, already_visited):
        self._test.assertEqual(
            self._expected_expected_event_stream.pop(0),
            ("on_node_enter", node.value, already_visited),
        )

    def on_node_exit(self, node):
        self._test.assertEqual(
            self._expected_expected_event_stream.pop(0),
            ("on_node_exit", node.value),
        )


class GraphWalkerTest(base.TestCase):
    def test_graph_walker(self):
        test_matrix = (
            ({
                'A': ['B'],
                'B': ['C'],
                'C': [],
            }, (
                ("on_node_enter", 'A', False),
                ("on_node_enter", 'B', False),
                ("on_node_enter", 'C', False),
                ("on_node_exit", 'C'),
                ("on_node_exit", 'B'),
                ("on_node_exit", 'A'),
            )),
            ({
                'A': ['C'],
                'B': ['C'],
                'C': [],
            }, (
                ("on_node_enter", 'A', False),
                ("on_node_enter", 'C', False),
                ("on_node_exit", 'C'),
                ("on_node_exit", 'A'),
                ("on_node_enter", 'B', False),
                ("on_node_enter", 'C', True),
                ("on_node_exit", 'C'),
                ("on_node_exit", 'B'),
            )),
            ({
                'A': ['C'],
                'B': ['C'],
                'C': ['D', 'E'],
                'D': [],
                'E': [],
            }, (
                ("on_node_enter", 'A', False),
                ("on_node_enter", 'C', False),
                ("on_node_enter", 'D', False),
                ("on_node_exit", 'D'),
                ("on_node_enter", 'E', False),
                ("on_node_exit", 'E'),
                ("on_node_exit", 'C'),
                ("on_node_exit", 'A'),
                ("on_node_enter", 'B', False),
                ("on_node_enter", 'C', True),
                ("on_node_enter", 'D', True),
                ("on_node_exit", 'D'),
                ("on_node_enter", 'E', True),
                ("on_node_exit", 'E'),
                ("on_node_exit", 'C'),
                ("on_node_exit", 'B'),
            )),
        )

        for g, expected_calls in test_matrix:
            listener = _TestGraphWalkerListener(expected_calls, self)
            walker = graph.GraphWalker()
            walker.register_listener(listener)
            keys = list(g.keys())
            keys.sort()
            walker.walk_graph(graph.build_graph(keys, g.__getitem__))
