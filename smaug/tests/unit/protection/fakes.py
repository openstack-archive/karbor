# Copyright 2010 OpenStack Foundation
# All Rights Reserved.
#
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

import futurist

from oslo_log import log as logging

from smaug.i18n import _LE
from smaug.resource import Resource
from smaug.services.protection.graph import build_graph

from taskflow import engines
from taskflow.patterns import graph_flow
from taskflow.patterns import linear_flow

A = Resource(id='A', type='fake', name='fake')
B = Resource(id='B', type='fake', name='fake')
C = Resource(id='C', type='fake', name='fake')
D = Resource(id='D', type='fake', name='fake')
E = Resource(id='E', type='fake', name='fake')

resource_map = {
    A: [C],
    B: [C],
    C: [D, E],
    D: [],
    E: [],
}
resource_graph = build_graph([A, B, C, D], resource_map.__getitem__)


def fake_protection_plan():
    protection_plan = {'id': 'fake_id',
                       'is_enabled': True,
                       'name': 'fake_protection_plan',
                       'comments': '',
                       'revision': 0,
                       'resources': [],
                       'protection_provider': None,
                       'parameters': {},
                       'provider_id': 'fake_id'
                       }
    return protection_plan


def fake_restore():
    restore = {
        'id': 'fake_id',
        'provider_id': 'fake_provider_id',
        'checkpoint_id': 'fake_checkpoint_id',
        'parameters': {
            'username': 'fake_username',
            'password': 'fake_password'
        },
        'restore_target': 'fake_target_url',
    }
    return restore


class FakeProtectablePlugin(object):
    def get_resource_type(self):
        pass

    def get_parent_resource_types(self):
        pass

    def list_resources(self):
        pass

    def get_dependent_resources(self, parent_resource):
        pass


LOG = logging.getLogger(__name__)


class FakeCheckpoint(object):
    def __init__(self):
        self.id = 'fake_checkpoint'
        self.status = 'available'
        self.resource_graph = resource_graph

    def purge(self):
        pass

    def commit(self):
        pass


class FakeCheckpointCollection(object):
    def create(self, plan):
        return FakeCheckpoint()

    def get(self, checkpoint_id):
        return FakeCheckpoint()


class FakeProvider(object):
    def __init__(self):
        self.id = 'test'
        self.name = 'provider'
        self.description = 'fake_provider'
        self.extend_info_schema = {}

    def build_task_flow(self, plan):
        status_getters = []
        return {'status_getters': status_getters,
                'task_flow': graph_flow.Flow('fake_flow')
                }

    def get_checkpoint_collection(self):
        return FakeCheckpointCollection()


class FakeFlowEngine(object):
    def __init__(self):
        super(FakeFlowEngine, self).__init__()

    def add_tasks(self, flow, *nodes, **kwargs):
        if flow is None:
            LOG.error(_LE("The flow is None,get it first"))
        flow.add(*nodes, **kwargs)

    def build_flow(self, flow_name, flow_type='graph'):
        if flow_type == 'linear':
            return linear_flow.Flow(flow_name)
        elif flow_type == 'graph':
            return graph_flow.Flow(flow_name)
        else:
            LOG.error(_LE("unsupported flow type:%s"), flow_type)
            return

    def get_engine(self, flow, **kwargs):
        if flow is None:
            LOG.error(_LE("Flow is None,build it first"))
            return
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

    def run_engine(self, flow_engine):
        if flow_engine is None:
            LOG.error(_LE("Flow engine is None,get it first"))
            return
        flow_engine.run()

    def output(self, flow_engine, target=None):
        if flow_engine is None:
            LOG.error(_LE("Flow engine is None,return nothing"))
            return
        if target:
            return flow_engine.storage.fetch(target)
        return flow_engine.storage.fetch_all()
