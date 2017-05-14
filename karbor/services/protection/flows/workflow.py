# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import abc
import futurist
import six

from karbor import exception
from karbor.i18n import _
from oslo_log import log as logging

from taskflow import engines
from taskflow.patterns import graph_flow
from taskflow.patterns import linear_flow
from taskflow import task


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class WorkFlowEngine(object):
    @abc.abstractmethod
    def build_flow(self, flow_name, flow_type='graph'):
        """build flow

        :param flow_name: the flow name
        :param flow_type:'linear' or 'graph',default:'graph'
        :return:linear flow or graph flow
        """
        return

    @abc.abstractmethod
    def get_engine(self, flow, **kwargs):
        return

    @abc.abstractmethod
    def run_engine(self, flow_engine):
        return

    @abc.abstractmethod
    def output(self, flow_engine, target=None):
        return

    @abc.abstractmethod
    def create_task(self, function, requires=None, provides=None,
                    inject=None, **kwargs):
        """create a task

        :param function:make a task from this callable
        :param requires: A OrderedSet of inputs this task requires to function.
        :param provides:A set, string or list of items that this will be
                         providing (or could provide) to others
        :param inject:An immutable input_name => value dictionary which
                       specifies any initial inputs that should be
                       automatically injected into the task scope before the
                       task execution commences
        """
        return

    @abc.abstractmethod
    def link_task(self, flow, u, v):
        """Link existing node as a runtime dependency of existing node v

        :param u: task or flow to create a link from (must exist already)
        :param v: task or flow to create a link to (must exist already)
        :param flow: graph flow
        """
        return

    @abc.abstractmethod
    def add_tasks(self, flow, *nodes, **kwargs):
        return

    @abc.abstractmethod
    def search_task(self, flow, task_id):
        return


class TaskFlowEngine(WorkFlowEngine):
    def build_flow(self, flow_name, flow_type='graph'):
        if flow_type == 'linear':
            return linear_flow.Flow(flow_name)
        elif flow_type == 'graph':
            return graph_flow.Flow(flow_name)
        else:
            raise ValueError(_("unsupported flow type: %s") % flow_type)

    def get_engine(self, flow, **kwargs):
        if flow is None:
            LOG.error("The flow is None, build it first")
            raise exception.InvalidTaskFlowObject(
                reason=_("The flow is None"))
        executor = kwargs.get('executor', None)
        engine = kwargs.get('engine', None)
        store = kwargs.get('store', None)
        if not executor:
            executor = futurist.GreenThreadPoolExecutor()
        if not engine:
            engine = 'parallel'
        flow_engine = engines.load(flow,
                                   executor=executor,
                                   engine=engine,
                                   store=store)
        return flow_engine

    def karbor_flow_watch(self, state, details):
        LOG.trace("The Flow [%s] OldState[%s] changed to State[%s]: ",
                  details.get('task_name'), details.get('old_state'), state)

    def karbor_atom_watch(self, state, details):
        LOG.trace("The Task [%s] OldState[%s] changed to State[%s]: ",
                  details.get('task_name'), details.get('old_state'), state)

    def run_engine(self, flow_engine):
        if flow_engine is None:
            LOG.error("Flow engine is None,get it first")
            raise exception.InvalidTaskFlowObject(
                reason=_("The flow_engine is None"))

        flow_engine.notifier.register('*', self.karbor_flow_watch)
        flow_engine.atom_notifier.register('*', self.karbor_atom_watch)
        flow_engine.run()

    def output(self, flow_engine, target=None):
        if flow_engine is None:
            LOG.error("Flow engine is None,return nothing")
            raise exception.InvalidTaskFlowObject(
                reason=_("The flow_engine is None"))
        if target:
            return flow_engine.storage.fetch(target)
        return flow_engine.storage.fetch_all()

    def create_task(self, function, requires=None, provides=None,
                    inject=None, **kwargs):
        name = kwargs.get('name', None)
        auto_extract = kwargs.get('auto_extract', True)
        rebind = kwargs.get('rebind', None)
        revert = kwargs.get('revert', None)
        version = kwargs.get('version', None)
        if function:
            return task.FunctorTask(function,
                                    name=name,
                                    provides=provides,
                                    requires=requires,
                                    auto_extract=auto_extract,
                                    rebind=rebind,
                                    revert=revert,
                                    version=version,
                                    inject=inject)

    def link_task(self, flow, u, v):
        if flow is None:
            LOG.error("The flow is None, build it first")
            raise exception.InvalidTaskFlowObject(
                reason=_("The flow is None"))
        if u and v:
            flow.link(u, v)

    def add_tasks(self, flow, *nodes, **kwargs):
        if flow is None:
            LOG.error("The flow is None, get it first")
            raise exception.InvalidTaskFlowObject(
                reason=_("The flow is None"))
        flow.add(*nodes, **kwargs)

    def search_task(self, flow, task_id):
        if not isinstance(flow, graph_flow.Flow):
            LOG.error("this is not a graph flow,flow name:%s", flow.name)
            return
        for node, meta in flow.iter_nodes():
            if not isinstance(node, task.FunctorTask):
                continue
            if task_id == getattr(node, 'name'):
                return node
