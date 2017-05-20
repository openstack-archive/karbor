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

from functools import partial
import mock

from karbor.common import constants
from karbor.resource import Resource
from karbor.services.protection.flows.workflow import TaskFlowEngine
from karbor.services.protection import graph
from karbor.services.protection import resource_flow
from karbor.services.protection import restore_heat
from karbor.tests import base
from karbor.tests.unit.protection import fakes
from oslo_config import cfg

CONF = cfg.CONF

(
    parent_type,
    child_type,
    grandchild_type,
) = fakes.FakeProtectionPlugin.SUPPORTED_RESOURCES

parent = Resource(id='A1', name='parent', type=parent_type)
child = Resource(id='B1', name='child', type=child_type)
grandchild = Resource(id='C1', name='grandchild', type=grandchild_type)


class ResourceFlowTest(base.TestCase):
    def setUp(self):
        super(ResourceFlowTest, self).setUp()

        self.resource_graph = {
            parent: [child],
            child: [grandchild],
            grandchild: [],
        }

        self.provider = fakes.FakeProvider()
        self.test_graph = graph.build_graph([parent],
                                            self.resource_graph.__getitem__)
        self.taskflow_engine = TaskFlowEngine()

    def _walk_operation(self, protection, operation_type,
                        checkpoint='checkpoint', parameters={}, context=None,
                        **kwargs):
        plugin_map = {
            parent_type: protection,
            child_type: protection,
            grandchild_type: protection,
        }
        flow = resource_flow.build_resource_flow(operation_type,
                                                 context,
                                                 self.taskflow_engine,
                                                 plugin_map,
                                                 self.test_graph,
                                                 parameters)

        store = {
            'checkpoint': checkpoint
        }
        store.update(kwargs)

        engine = self.taskflow_engine.get_engine(flow,
                                                 engine='parallel',
                                                 store=store)
        self.taskflow_engine.run_engine(engine)

    @mock.patch('karbor.tests.unit.protection.fakes.FakeProtectionPlugin')
    def test_resource_no_impl(self, mock_protection):
        for operation in constants.OPERATION_TYPES:
            kwargs = {}
            if operation == constants.OPERATION_RESTORE:
                kwargs['heat_template'] = restore_heat.HeatTemplate()
                kwargs['restore'] = None
            self._walk_operation(mock_protection, operation, **kwargs)

    @mock.patch('karbor.tests.unit.protection.fakes.FakeProtectionPlugin')
    def test_resource_flow_callbacks(self, mock_protection):
        for operation in constants.OPERATION_TYPES:
            mock_operation = fakes.MockOperation()
            get_operation_attr = 'get_{}_operation'.format(operation)
            getattr(
                mock_protection,
                get_operation_attr
            ).return_value = mock_operation

            kwargs = {}
            if operation == constants.OPERATION_RESTORE:
                kwargs['heat_template'] = restore_heat.HeatTemplate()
                kwargs['restore'] = None
            self._walk_operation(mock_protection, operation, **kwargs)

            self.assertEqual(mock_operation.on_prepare_begin.call_count,
                             len(self.resource_graph))
            self.assertEqual(mock_operation.on_prepare_finish.call_count,
                             len(self.resource_graph))
            self.assertEqual(mock_operation.on_main.call_count,
                             len(self.resource_graph))
            self.assertEqual(mock_operation.on_complete.call_count,
                             len(self.resource_graph))

    @mock.patch('karbor.tests.unit.protection.fakes.FakeProtectionPlugin')
    def test_resource_flow_parameters(self, mock_protection):
        resource_a1_id = "{}#{}".format(parent_type, 'A1')
        resource_b1_id = "{}#{}".format(child_type, 'B1')
        parameters = {
            resource_a1_id: {'option1': 'value1'},
            resource_b1_id: {'option2': 'value2', 'option3': 'value3'},
            parent_type: {'option4': 'value4'},
            child_type: {'option3': 'value5'}
        }

        for operation in constants.OPERATION_TYPES:
            mock_operation = fakes.MockOperation()
            get_operation_attr = 'get_{}_operation'.format(operation)
            getattr(
                mock_protection,
                get_operation_attr
            ).return_value = mock_operation

            kwargs = {
                'checkpoint': 'A',
                'context': 'B',
            }

            if operation == constants.OPERATION_RESTORE:
                kwargs['heat_template'] = restore_heat.HeatTemplate()
                kwargs['restore'] = None

            self._walk_operation(mock_protection, operation,
                                 parameters=parameters, **kwargs)

            for resource in self.resource_graph:
                resource_params = parameters.get(resource.type, {})
                resource_id = '{}#{}'.format(resource.type, resource.id)
                resource_params.update(parameters.get(resource_id, {}))
                mock_operation.on_prepare_begin.assert_any_call(
                    resource=resource,
                    parameters=resource_params,
                    **kwargs)
                mock_operation.on_prepare_finish.assert_any_call(
                    resource=resource,
                    parameters=resource_params,
                    **kwargs)
                mock_operation.on_main.assert_any_call(
                    resource=resource,
                    parameters=resource_params,
                    **kwargs)
                mock_operation.on_complete.assert_any_call(
                    resource=resource,
                    parameters=resource_params,
                    **kwargs)

    @mock.patch('karbor.tests.unit.protection.fakes.FakeProtectionPlugin')
    def test_resource_flow_order(self, mock_protection):
        def test_order(order_list, hook_type, resource, *args, **kwargs):
            order_list.append((hook_type, resource.id))

        operation = constants.OPERATION_PROTECT
        mock_operation = fakes.MockOperation()
        get_operation_attr = 'get_{}_operation'.format(operation)
        getattr(
            mock_protection,
            get_operation_attr
        ).return_value = mock_operation

        order_list = []
        mock_operation.on_prepare_begin = partial(test_order, order_list,
                                                  'pre_begin')
        mock_operation.on_prepare_finish = partial(test_order, order_list,
                                                   'pre_finish')
        mock_operation.on_main = partial(test_order, order_list, 'main')
        mock_operation.on_complete = partial(test_order, order_list,
                                             'complete')

        self._walk_operation(mock_protection, operation)

        self.assertLess(order_list.index(('pre_begin', parent.id)),
                        order_list.index(('pre_begin', child.id)))
        self.assertLess(order_list.index(('pre_begin', child.id)),
                        order_list.index(('pre_begin', grandchild.id)))

        self.assertGreater(order_list.index(('pre_finish', parent.id)),
                           order_list.index(('pre_finish', child.id)))
        self.assertGreater(order_list.index(('pre_finish', child.id)),
                           order_list.index(('pre_finish', grandchild.id)))

        self.assertGreater(order_list.index(('complete', parent.id)),
                           order_list.index(('complete', child.id)))
        self.assertGreater(order_list.index(('complete', child.id)),
                           order_list.index(('complete', grandchild.id)))

        for resource_id in (parent.id, child.id, grandchild.id):
            self.assertLess(order_list.index(('pre_begin', resource_id)),
                            order_list.index(('pre_finish', resource_id)))
            self.assertLess(order_list.index(('pre_finish', resource_id)),
                            order_list.index(('main', resource_id)))
            self.assertLess(order_list.index(('main', resource_id)),
                            order_list.index(('complete', resource_id)))
