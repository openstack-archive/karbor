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
import mock

from oslo_config import cfg
from oslo_log import log as logging

from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection.graph import build_graph
from karbor.services.protection import protection_plugin
from karbor.services.protection import provider
from karbor.services.protection import resource_flow

from taskflow import engines
from taskflow.patterns import graph_flow
from taskflow.patterns import linear_flow
from taskflow import task

LOG = logging.getLogger(__name__)

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
                       'resources': [
                           {"id": "A", "type": "fake", "name": "fake"},
                           {"id": "B", "type": "fake", "name": "fake"},
                           {"id": "C", "type": "fake", "name": "fake"},
                           {"id": "D", "type": "fake", "name": "fake"}],
                       'protection_provider': None,
                       'parameters': {},
                       'provider_id': 'fake_id'
                       }
    return protection_plan


plan_resources = [A, B, C, D]


class FakeBankPlugin(BankPlugin):
    def __init__(self, config=None):
        super(FakeBankPlugin, self).__init__(config=config)
        self._objects = {}
        fake_bank_opts = [
            cfg.HostAddressOpt('fake_host'),
        ]
        if config:
            config.register_opts(fake_bank_opts, 'fake_bank')
            self.fake_host = config['fake_bank']['fake_host']

    def update_object(self, key, value):
        self._objects[key] = value

    def get_object(self, key):
        value = self._objects.get(key, None)
        if value is None:
            raise Exception
        return value

    def list_objects(self, prefix=None, limit=None, marker=None):
        objects_name = []
        if prefix is not None:
            for key, value in self._objects.items():
                if key.find(prefix) == 0:
                    objects_name.append(key.lstrip(prefix))
        else:
            objects_name = self._objects.keys()
        return objects_name

    def delete_object(self, key):
        self._objects.pop(key)

    def get_owner_id(self):
        return


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


class MockOperation(protection_plugin.Operation):
    def __init__(self):
        super(MockOperation, self).__init__()
        for hook_name in resource_flow.HOOKS:
            setattr(self, hook_name, mock.Mock())


class FakeProtectionPlugin(protection_plugin.ProtectionPlugin):
    SUPPORTED_RESOURCES = [
        'Test::ResourceA',
        'Test::ResourceB',
        'Test::ResourceC',
    ]

    def __init__(self, config=None, *args, **kwargs):
        super(FakeProtectionPlugin, self).__init__(config)
        fake_plugin_opts = [
            cfg.StrOpt('fake_user'),
        ]
        if config:
            config.register_opts(fake_plugin_opts, 'fake_plugin')
            self.fake_user = config['fake_plugin']['fake_user']

    def get_protect_operation(self, *args, **kwargs):
        return MockOperation()

    def get_restore_operation(self, *args, **kwargs):
        return MockOperation()

    def get_delete_operation(self, *args, **kwargs):
        return MockOperation()

    @classmethod
    def get_supported_resources_types(cls):
        return cls.SUPPORTED_RESOURCES

    @classmethod
    def get_options_schema(cls, resource_type):
        return {}

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        return {}

    @classmethod
    def get_restore_schema(cls, resource_type):
        return {}

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        return None


class FakeCheckpoint(object):
    def __init__(self):
        super(FakeCheckpoint, self).__init__()
        self.id = 'fake_checkpoint'
        self.status = 'available'
        self.resource_graph = resource_graph

    def purge(self):
        pass

    def commit(self):
        pass

    def get_resource_bank_section(self, resource_id):
        bank = Bank(FakeBankPlugin())
        return BankSection(bank, resource_id)

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "resource_graph": self.resource_graph,
            "protection_plan": None,
            "project_id": None
        }


class FakeCheckpointCollection(object):
    def create(self, plan, checkpoint_properties=None):
        return FakeCheckpoint()

    def get(self, checkpoint_id):
        return FakeCheckpoint()


class FakeProvider(provider.PluggableProtectionProvider):
    def __init__(self):
        self._id = 'test'
        self._name = 'provider'
        self._description = 'fake_provider'
        self._extend_info_schema = {}
        self._config = None
        self._plugin_map = {
            'fake': FakeProtectionPlugin,
        }

    def get_checkpoint_collection(self):
        return FakeCheckpointCollection()


class FakeFlowEngine(object):
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

    def add_tasks(self, flow, *nodes, **kwargs):
        if flow is None:
            LOG.error("The flow is None, get it first")
        flow.add(*nodes, **kwargs)

    def link_task(self, flow, u, v):
        flow.link(u, v)

    def build_flow(self, flow_name, flow_type='graph'):
        if flow_type == 'linear':
            return linear_flow.Flow(flow_name)
        elif flow_type == 'graph':
            return graph_flow.Flow(flow_name)
        else:
            LOG.error("unsupported flow type:%s", flow_type)
            return

    def get_engine(self, flow, **kwargs):
        if flow is None:
            LOG.error("Flow is None, build it first")
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
            LOG.error("Flow engine is None,get it first")
            return
        flow_engine.run()

    def output(self, flow_engine, target=None):
        if flow_engine is None:
            LOG.error("Flow engine is None,return nothing")
            return
        if target:
            return flow_engine.storage.fetch(target)
        return flow_engine.storage.fetch_all()
