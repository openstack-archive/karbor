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
