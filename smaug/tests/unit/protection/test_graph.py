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

import smaug.services.protection.graph as graph
from smaug.tests import base


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


class _TestGraphWalkerListener(graph.GraphWalkerListener):
    def __init__(self, expected_event_stream, test):
        # Because the testing famework is badly designed
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
            keys = g.keys()
            keys.sort()
            walker.walk_graph(graph.build_graph(keys, g.__getitem__))