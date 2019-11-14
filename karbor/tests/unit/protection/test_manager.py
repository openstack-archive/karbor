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

import mock

from oslo_config import cfg
import oslo_messaging

from karbor import exception
from karbor.resource import Resource
from karbor.services.protection.flows import utils
from karbor.services.protection.flows import worker as flow_manager
from karbor.services.protection import manager
from karbor.services.protection import protectable_registry
from karbor.services.protection import provider

from karbor.tests import base
from karbor.tests.unit.protection import fakes

CONF = cfg.CONF
CONF.import_opt('trigger_poll_interval', 'karbor.services.operationengine'
                '.engine.triggers.timetrigger')


class ProtectionServiceTest(base.TestCase):
    def setUp(self):
        self.load_engine = flow_manager.Worker._load_engine
        flow_manager.Worker._load_engine = mock.Mock()
        flow_manager.Worker._load_engine.return_value = fakes.FakeFlowEngine()
        super(ProtectionServiceTest, self).setUp()
        self.pro_manager = manager.ProtectionManager()
        self.protection_plan = fakes.fake_protection_plan()

    @mock.patch.object(protectable_registry.ProtectableRegistry,
                       'list_resource_types')
    def test_list_protectable_types(self, mocker):
        expected = ["OS::Nova::Server",
                    "OS::Cinder::Volume"]
        mocker.return_value = expected
        result = self.pro_manager.list_protectable_types(None)
        self.assertEqual(expected, result)

    def test_show_protectable_type(self):
        def mock_plugins(self):
            self._plugin_map = {
                "OS::Nova::Server": server_plugin,
                "OS::Cinder::Volume": volume_plugin
            }

        server_plugin = fakes.FakeProtectablePlugin()
        server_plugin.get_resource_type = mock.MagicMock(
            return_value="OS::Nova::Server")
        volume_plugin = fakes.FakeProtectablePlugin()
        volume_plugin.get_parent_resource_types = mock.MagicMock(
            return_value=["OS::Nova::Server"])

        protectable_registry.ProtectableRegistry.load_plugins = mock_plugins

        result = self.pro_manager.show_protectable_type(None,
                                                        "OS::Nova::Server")
        self.assertEqual("OS::Nova::Server", result["name"])
        self.assertEqual({"OS::Cinder::Volume", "OS::Glance::Image"},
                         set(result["dependent_types"]))

    @mock.patch.object(protectable_registry.ProtectableRegistry,
                       'show_resource')
    def test_show_protectable_instance(self, mocker):
        mocker.return_value = Resource(type='OS::Nova::Server',
                                       id='123456',
                                       name='name123')
        fake_cntx = mock.MagicMock()

        result = self.pro_manager.show_protectable_instance(
            fake_cntx, 'OS::Nova::Server', '123456')
        self.assertEqual(
            {'id': '123456', 'name': 'name123', 'type': 'OS::Nova::Server',
             'extra_info': None},
            result)

    @mock.patch.object(protectable_registry.ProtectableRegistry,
                       'show_resource')
    def test_show_protectable_instance_with_nonexist_id(self, mocker):
        mocker.return_value = None
        fake_cntx = mock.MagicMock()

        result = self.pro_manager.show_protectable_instance(
            fake_cntx, 'OS::Nova::Server', '123456')
        self.assertEqual(None, result)

    @mock.patch.object(protectable_registry.ProtectableRegistry,
                       'list_resources')
    def test_list_protectable_instances(self, mocker):
        mocker.return_value = [Resource(type='OS::Nova::Server',
                                        id='123456',
                                        name='name123'),
                               Resource(type='OS::Nova::Server',
                                        id='654321',
                                        name='name654')]
        fake_cntx = mock.MagicMock()

        result = self.pro_manager.list_protectable_instances(
            fake_cntx, 'OS::Nova::Server')
        self.assertEqual([{'id': '123456', 'name': 'name123',
                           'extra_info': None},
                          {'id': '654321', 'name': 'name654',
                           'extra_info': None}],
                         result)

    @mock.patch.object(protectable_registry.ProtectableRegistry,
                       'fetch_dependent_resources')
    def test_list_protectable_dependents(self, mocker):
        mocker.return_value = [Resource(type='OS::Cinder::Volume',
                                        id='123456', name='name123'),
                               Resource(type='OS::Cinder::Volume',
                                        id='654321', name='name654')]
        fake_cntx = mock.MagicMock()

        result = self.pro_manager.list_protectable_dependents(
            fake_cntx, 'fake_id', 'OS::Nova::Server', "")
        self.assertEqual([{'type': 'OS::Cinder::Volume', 'id': '123456',
                           'name': 'name123', 'extra_info': None},
                          {'type': 'OS::Cinder::Volume', 'id': '654321',
                           'name': 'name654', 'extra_info': None}],
                         result)

    @mock.patch.object(utils, 'update_operation_log')
    @mock.patch.object(utils, 'create_operation_log')
    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_protect(self, mock_provider, mock_operation_log_create,
                     mock_operation_log_update):
        mock_provider.return_value = fakes.FakeProvider()
        self.pro_manager.protect(None, fakes.fake_protection_plan())

    @mock.patch.object(flow_manager.Worker, 'get_flow')
    def test_protect_in_error(self, mock_flow):
        mock_flow.side_effect = Exception()
        self.assertRaises(oslo_messaging.ExpectedException,
                          self.pro_manager.protect,
                          None,
                          fakes.fake_protection_plan())

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_restore_with_project_id_not_same(self, mock_provider):
        mock_provider.return_value = fakes.FakeProvider()
        context = mock.MagicMock(project_id='fake_project_id_1',
                                 is_admin=False)
        fake_restore = {
            'checkpoint_id': 'fake_checkpoint',
            'provider_id': 'fake_provider_id',
            'parameters': None
        }
        self.assertRaises(
            oslo_messaging.ExpectedException, self.pro_manager.restore,
            context, fake_restore, None)

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_list_checkpoints(self, mock_provider):
        fake_provider = fakes.FakeProvider()
        fake_provider.list_checkpoints = mock.MagicMock()
        mock_provider.return_value = fake_provider
        context = mock.MagicMock(project_id='fake_project_id')
        self.pro_manager.list_checkpoints(context, 'provider1', filters={},
                                          all_tenants=False)
        fake_provider.list_checkpoints.assert_called_once_with(
            'fake_project_id', 'provider1', limit=None, marker=None,
            plan_id=None, start_date=None, end_date=None,
            sort_dir=None, context=context, all_tenants=False)

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_list_checkpoints_with_all_tenants(self, mock_provider):
        fake_provider = fakes.FakeProvider()
        fake_provider.list_checkpoints = mock.MagicMock()
        mock_provider.return_value = fake_provider
        context = mock.MagicMock(project_id='fake_project_id')
        self.pro_manager.list_checkpoints(context, 'provider1', filters={},
                                          all_tenants=True)
        fake_provider.list_checkpoints.assert_called_once_with(
            'fake_project_id', 'provider1', limit=None, marker=None,
            plan_id=None, start_date=None, end_date=None,
            sort_dir=None, context=context, all_tenants=True)

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_list_checkpoints_with_all_tenants_and_filter_by_project_id(
            self, mock_provider):
        fake_provider = fakes.FakeProvider()
        fake_provider.list_checkpoints = mock.MagicMock()
        mock_provider.return_value = fake_provider
        context = mock.MagicMock(project_id='fake_project_id')
        self.pro_manager.list_checkpoints(context, 'provider1', filters={
            'project_id': 'fake_project_id1'}, all_tenants=True)
        fake_provider.list_checkpoints.assert_called_once_with(
            'fake_project_id1', 'provider1', limit=None, marker=None,
            plan_id=None, start_date=None, end_date=None,
            sort_dir=None, context=context, all_tenants=False)

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_show_checkpoint(self, mock_provider):
        mock_provider.return_value = fakes.FakeProvider()
        context = mock.MagicMock(project_id='fake_project_id')
        cp = self.pro_manager.show_checkpoint(context, 'provider1',
                                              'fake_checkpoint')
        self.assertEqual('fake_checkpoint', cp['id'])

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_show_checkpoint_not_allowed(self, mock_provider):
        mock_provider.return_value = fakes.FakeProvider()
        context = mock.MagicMock(
            project_id='fake_project_id_1',
            is_admin=False
        )
        self.assertRaises(oslo_messaging.ExpectedException,
                          self.pro_manager.show_checkpoint,
                          context, 'provider1', 'fake_checkpoint')

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    @mock.patch.object(fakes.FakeCheckpointCollection, 'get')
    def test_show_checkpoint_not_found(self, mock_cp_collection_get,
                                       mock_provider):
        mock_provider.return_value = fakes.FakeProvider()
        context = mock.MagicMock()
        mock_cp_collection_get.side_effect = exception.CheckpointNotFound(
            checkpoint_id='123')
        self.assertRaises(oslo_messaging.ExpectedException,
                          self.pro_manager.show_checkpoint,
                          context,
                          'provider1',
                          'non_existent_checkpoint')

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_checkpoint_state_reset(self, mock_provider):
        fake_provider = fakes.FakeProvider()
        fake_checkpoint = fakes.FakeCheckpoint()
        fake_checkpoint.commit = mock.MagicMock()
        fake_provider.get_checkpoint = mock.MagicMock(
            return_value=fake_checkpoint)
        mock_provider.return_value = fake_provider
        context = mock.MagicMock(project_id='fake_project_id', is_admin=True)
        self.pro_manager.reset_state(context, 'provider1', 'fake_checkpoint',
                                     'error')
        self.assertEqual(fake_checkpoint.status, 'error')
        self.assertEqual(True, fake_checkpoint.commit.called)

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_checkpoint_state_reset_with_access_not_allowed(
            self, mock_provider):
        fake_provider = fakes.FakeProvider()
        fake_checkpoint = fakes.FakeCheckpoint()
        fake_provider.get_checkpoint = mock.MagicMock(
            return_value=fake_checkpoint)
        mock_provider.return_value = fake_provider
        context = mock.MagicMock(project_id='fake_project_id_01',
                                 is_admin=False)
        self.assertRaises(oslo_messaging.ExpectedException,
                          self.pro_manager.reset_state,
                          context,
                          'fake_project_id',
                          'fake_checkpoint_id',
                          'error')

    @mock.patch.object(provider.ProviderRegistry, 'show_provider')
    def test_checkpoint_state_reset_with_wrong_checkpoint_state(
            self, mock_provider):
        fake_provider = fakes.FakeProvider()
        fake_checkpoint = fakes.FakeCheckpoint()
        fake_checkpoint.status = 'deleting'
        fake_provider.get_checkpoint = mock.MagicMock(
            return_value=fake_checkpoint)
        mock_provider.return_value = fake_provider
        context = mock.MagicMock(project_id='fake_project_id', is_admin=True)
        self.assertRaises(oslo_messaging.ExpectedException,
                          self.pro_manager.reset_state,
                          context,
                          'fake_project_id',
                          'fake_checkpoint_id',
                          'error')

    def tearDown(self):
        flow_manager.Worker._load_engine = self.load_engine
        super(ProtectionServiceTest, self).tearDown()
