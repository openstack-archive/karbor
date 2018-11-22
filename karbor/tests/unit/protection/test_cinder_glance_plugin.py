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

import collections
from karbor.common import constants
from karbor.context import RequestContext
from karbor import exception
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection import client_factory
from karbor.services.protection.protection_plugins.volume.\
    volume_glance_plugin import VolumeGlanceProtectionPlugin
from karbor.services.protection.protection_plugins.volume import \
    volume_glance_plugin_schemas
from karbor.tests import base
import mock
from oslo_config import cfg
from oslo_config import fixture


class FakeBankPlugin(BankPlugin):
    def update_object(self, key, value, context=None):
        return

    def get_object(self, key, context=None):
        return

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None, context=None):
        return

    def delete_object(self, key, context=None):
        return

    def get_owner_id(self, context=None):
        return


fake_bank = Bank(FakeBankPlugin())
fake_bank_section = BankSection(bank=fake_bank, section="fake")

ResourceNode = collections.namedtuple(
    "ResourceNode",
    ["value",
     "child_nodes"]
)


Volume = collections.namedtuple(
    "Volume",
    ["id", "status", "size"]
)

Snapshot = collections.namedtuple(
    "Snapshot",
    ["id", "status", "size"]
)

Image = collections.namedtuple(
    "Image",
    ["disk_format",
     "container_format",
     "status",
     "id"]
)


def call_hooks(operation, checkpoint, resource, context, parameters, **kwargs):
    def noop(*args, **kwargs):
        pass

    hooks = (
        'on_prepare_begin',
        'on_prepare_finish',
        'on_main',
        'on_complete',
    )
    for hook_name in hooks:
        hook = getattr(operation, hook_name, noop)
        hook(checkpoint, resource, context, parameters, **kwargs)


class FakeCheckpoint(object):
    def __init__(self):
        super(FakeCheckpoint, self).__init__()
        self.bank_section = fake_bank_section

    def get_resource_bank_section(self, resource_id=None):
        return self.bank_section


class VolumeGlanceProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(VolumeGlanceProtectionPluginTest, self).setUp()

        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='volume_glance_plugin',
            poll_interval=0,
            backup_image_object_size=65536
        )
        self.plugin = VolumeGlanceProtectionPlugin(plugin_config)
        cfg.CONF.set_default('glance_endpoint',
                             'http://127.0.0.1:9292',
                             'glance_client')

        cfg.CONF.set_default('cinder_endpoint',
                             'http://127.0.0.1:8774/v2.1',
                             'cinder_client')
        self.cntxt = RequestContext(user_id='demo',
                                    project_id='abcd',
                                    auth_token='efgh'
                                    )
        self.cinder_client = client_factory.ClientFactory.create_client(
            "cinder", self.cntxt)
        self.glance_client = client_factory.ClientFactory.create_client(
            "glance", self.cntxt)
        self.checkpoint = FakeCheckpoint()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            constants.VOLUME_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         volume_glance_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            constants.VOLUME_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         volume_glance_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            constants.VOLUME_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         volume_glance_plugin_schemas.SAVED_INFO_SCHEMA)

    @mock.patch('karbor.services.protection.protection_plugins'
                '.utils.status_poll')
    @mock.patch('karbor.services.protection.clients.glance.create')
    @mock.patch('karbor.services.protection.clients.cinder.create')
    def test_create_backup(self, mock_cinder_create,
                           mock_glance_create, mock_status_poll):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.update_object = mock.MagicMock()

        protect_operation = self.plugin.get_protect_operation(resource)
        mock_cinder_create.return_value = self.cinder_client
        mock_glance_create.return_value = self.glance_client
        mock_status_poll.return_value = True
        self.cinder_client.volume_snapshots.create = mock.MagicMock()
        self.cinder_client.volume_snapshots.create.return_value = Snapshot(
            id="1234",
            status="available",
            size='100000000'
        )
        self.cinder_client.volume_snapshots.get = mock.MagicMock()
        self.cinder_client.volume_snapshots.get.return_value = Snapshot(
            id="1234",
            status="available",
            size='100000000'
        )
        self.cinder_client.volumes.create = mock.MagicMock()
        self.cinder_client.volumes.create.return_value = Volume(
            id='2345',
            status='available',
            size=1
        )
        self.cinder_client.volumes.get = mock.MagicMock()
        self.cinder_client.volumes.get.return_value = Volume(
            id='2345',
            status='available',
            size=1
        )
        self.cinder_client.volumes.upload_to_image = mock.MagicMock()
        self.cinder_client.volumes.upload_to_image.return_value = [202, {
            'os-volume_upload_image': {
                'image_id': "3456"
            }
        }]

        self.glance_client.images.get = mock.MagicMock()
        self.glance_client.images.return_value = Image(
            disk_format="raw",
            container_format="bare",
            status="active",
            id="3456"
        )
        fake_bank_section.update_object = mock.MagicMock()
        self.glance_client.images.data = mock.MagicMock()
        self.glance_client.images.data.return_value = []
        mock_status_poll.return_value = True

        self.cinder_client.volume_snapshots.delete = mock.MagicMock()
        self.cinder_client.volumes.delete = mock.MagicMock()
        self.glance_client.images.delete = mock.MagicMock()

        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})
        self.cinder_client.volumes.upload_to_image.assert_called_with(
            volume=Volume(id='2345', status='available', size=1),
            force=True,
            image_name='temporary_image_of_2345',
            container_format="bare",
            disk_format="raw",
            visibility="private",
            protected=False
        )

    def test_delete_backup(self):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.list_objects = mock.MagicMock()
        fake_bank_section.list_objects.return_value = ["data_1", "data_2"]
        fake_bank_section.delete_object = mock.MagicMock()
        delete_operation = self.plugin.get_delete_operation(resource)
        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual([constants.VOLUME_RESOURCE_TYPE], types)

    @mock.patch('karbor.services.protection.protection_plugins.utils.'
                'update_resource_verify_result')
    def test_verify_backup(self, mock_update_verify):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = 'available'

        verify_operation = self.plugin.get_verify_operation(resource)
        call_hooks(verify_operation, self.checkpoint, resource, self.cntxt,
                   {})
        mock_update_verify.assert_called_with(
            None, resource.type, resource.id, 'available')

    @mock.patch('karbor.services.protection.protection_plugins.utils.'
                'update_resource_verify_result')
    def test_verify_backup_with_error_status(self, mock_update_verify):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name='fake')
        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = 'error'

        verify_operation = self.plugin.get_verify_operation(resource)
        self.assertRaises(
            exception.VerifyResourceFailed, call_hooks, verify_operation,
            self.checkpoint, resource, self.cntxt, {})
        mock_update_verify.assert_called_with(
            None, resource.type, resource.id, 'error',
            'The status of volume backup status is error.')
