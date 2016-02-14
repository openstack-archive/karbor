# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
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
from collections import namedtuple

from oslo_log import log as logging

import six

from smaug.i18n import _


_GraphBuilderContext = namedtuple("_GraphBuilderContext", (
    "source_set",
    "encountered_set",
    "finished_nodes",
    "get_child_nodes",
))

GraphNode = namedtuple("GraphNode", (
    "value",
    "child_nodes",
))

LOG = logging.getLogger(__name__)


class FoundLoopError(RuntimeError):
    def __init__(self):
        super(FoundLoopError, self).__init__(
            _("A loop was found in the graph"))


def _build_graph_rec(context, node):
    LOG.trace("Entered node: %s", node)
    source_set = context.source_set
    encountered_set = context.encountered_set
    finished_nodes = context.finished_nodes
    LOG.trace("Gray set is %s", encountered_set)
    if node in encountered_set:
        raise FoundLoopError()

    LOG.trace("Black set is %s", finished_nodes.keys())
    if node in finished_nodes:
        return finished_nodes[node]

    LOG.trace("Change to gray: %s", node)
    encountered_set.add(node)
    child_nodes = context.get_child_nodes(node)
    LOG.trace("Child nodes are ", child_nodes)
    # If we found a parent than this is not a source
    source_set.difference_update(child_nodes)
    child_list = []
    for child_node in child_nodes:
        child_list.append(_build_graph_rec(context, child_node))

    LOG.trace("Change to black: ", node)
    encountered_set.discard(node)
    graph_node = GraphNode(value=node, child_nodes=tuple(child_list))
    finished_nodes[node] = graph_node

    return graph_node


def build_graph(start_nodes, get_child_nodes_func):
    context = _GraphBuilderContext(
        source_set=set(start_nodes),
        encountered_set=set(),
        finished_nodes={},
        get_child_nodes=get_child_nodes_func,
    )

    result = []
    for node in start_nodes:
        result.append(_build_graph_rec(context, node))

    assert(len(context.encountered_set) == 0)

    return [item for item in result if item.value in context.source_set]


@six.add_metaclass(abc.ABCMeta)
class GraphWalkerListener(object):
    """Interface for listening to GraphWaler events

    Classes that want to be able to use the graph walker to iterate over
    a graph should implement this interface.
    """
    @abc.abstractmethod
    def on_node_enter(self, node, already_visited):
        pass

    @abc.abstractmethod
    def on_node_exit(self, node):
        pass


class GraphWalker(object):
    def __init__(self):
        self._listeners = []

    def register_listener(self, graph_walker_listener):
        self._listeners.append(graph_walker_listener)

    def unregister_listener(self, graph_walker_listener):
        self._listeners.remove(graph_walker_listener)

    def walk_graph(self, source_nodes):
        self._walk_graph(source_nodes, set())

    def _walk_graph(self, source_nodes, visited_nodes):
        for node in source_nodes:
            for listener in self._listeners:
                listener.on_node_enter(node, node in visited_nodes)
                visited_nodes.add(node)

            self._walk_graph(node.child_nodes, visited_nodes)

            for listener in self._listeners:
                listener.on_node_exit(node)
