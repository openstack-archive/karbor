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
from oslo_serialization import jsonutils

import six

from karbor import exception
from karbor.i18n import _
from karbor.resource import Resource


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

PackedGraph = namedtuple('PackedGraph', ['nodes', 'adjacency'])

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
    LOG.trace("Child nodes are %s", child_nodes)
    # If we found a parent than this is not a source
    source_set.difference_update(child_nodes)
    child_list = []
    for child_node in child_nodes:
        child_list.append(_build_graph_rec(context, child_node))

    LOG.trace("Change to black: %s", node)
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
        super(GraphWalker, self).__init__()
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


class PackGraphWalker(GraphWalkerListener):
    """Pack a list of GraphNode

    Allocate a serialized id (sid) for every node and build an adjacency list,
    suitable for graph unpacking.
    """
    def __init__(self, adjacency_list, nodes_dict):
        super(PackGraphWalker, self).__init__()
        self._sid_counter = 0
        self._node_to_sid = {}
        self._adjacency_list = adjacency_list
        self._sid_to_node = nodes_dict

    def on_node_enter(self, node, already_visited):
        pass

    def on_node_exit(self, node):
        def key_serialize(key):
            return hex(key)

        if node not in self._node_to_sid:
            node_sid = self._sid_counter
            self._sid_counter += 1
            self._node_to_sid[node] = node_sid
            self._sid_to_node[key_serialize(node_sid)] = node.value

            if len(node.child_nodes) > 0:
                children_sids = map(lambda node:
                                    key_serialize(self._node_to_sid[node]),
                                    node.child_nodes)
                self._adjacency_list.append(
                    (key_serialize(node_sid), tuple(children_sids))
                )


def pack_graph(start_nodes):
    """Return a PackedGraph from a list of GraphNodes

    Packs a graph into a flat PackedGraph (nodes dictionary, adjacency list).
    """
    walker = GraphWalker()
    nodes_dict = {}
    adjacency_list = []
    packer = PackGraphWalker(adjacency_list, nodes_dict)
    walker.register_listener(packer)
    walker.walk_graph(start_nodes)
    return PackedGraph(nodes_dict, tuple(adjacency_list))


def unpack_graph(packed_graph):
    """Return a list of GraphNodes from a PackedGraph

    Unpacks a PackedGraph, which must have the property: each parent node in
    the adjacency list appears after its children.
    """
    (nodes, adjacency_list) = packed_graph
    nodes_dict = dict(nodes)
    graph_nodes_dict = {}

    for (parent_sid, children_sids) in adjacency_list:
        if parent_sid in graph_nodes_dict:
            raise exception.InvalidInput(
                reason=_("PackedGraph adjacency list must be topologically "
                         "ordered"))
        children = []
        for child_sid in children_sids:
            if child_sid not in graph_nodes_dict:
                graph_nodes_dict[child_sid] = GraphNode(
                    nodes_dict[child_sid], ())
            children.append(graph_nodes_dict[child_sid])
            nodes_dict.pop(child_sid, None)
        graph_nodes_dict[parent_sid] = GraphNode(nodes_dict[parent_sid],
                                                 tuple(children))

    result_nodes = []
    for sid in nodes_dict:
        if sid not in graph_nodes_dict:
            graph_nodes_dict[sid] = GraphNode(nodes_dict[sid], ())
        result_nodes.append(graph_nodes_dict[sid])
    return result_nodes


def serialize_resource_graph(resource_graph):
    packed_resource_graph = pack_graph(resource_graph)
    return jsonutils.dumps(
        packed_resource_graph,
        default=lambda r: (r.type, r.id, r.name, r.extra_info))


def deserialize_resource_graph(serialized_resource_graph):
    deserialized_graph = jsonutils.loads(serialized_resource_graph)
    packed_resource_graph = PackedGraph(nodes=deserialized_graph[0],
                                        adjacency=deserialized_graph[1])
    for sid, node in packed_resource_graph.nodes.items():
        packed_resource_graph.nodes[sid] = Resource(type=node[0],
                                                    id=node[1],
                                                    name=node[2],
                                                    extra_info=node[3])
    resource_graph = unpack_graph(packed_resource_graph)
    return resource_graph
