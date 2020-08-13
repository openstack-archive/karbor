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
from unittest import mock

from oslo_config import cfg
from oslo_config import fixture

from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection import client_factory
from karbor.services.protection.protection_plugins. \
    database.database_backup_plugin import DatabaseBackupProtectionPlugin
from karbor.services.protection.protection_plugins.database \
    import database_backup_plugin_schemas
from karbor.tests import base


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

Database = collections.namedtuple(
    "Database",
    ["status"]
)

Backup = collections.namedtuple(
    "Backup",
    ["id", "status"]
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
        self.bank_section = fake_bank_section

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class TroveProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(TroveProtectionPluginTest, self).setUp()

        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='database_backup_plugin',
            poll_interval=0,
        )

        self.plugin = DatabaseBackupProtectionPlugin(plugin_config)

        cfg.CONF.set_default('trove_endpoint',
                             'http://127.0.0.1:8774/v2.1',
                             'trove_client')
        service_catalog = [
            {'type': 'database',
             'endpoints': [{'publicURL': 'http://127.0.0.1:8774/v2.1/abcd'}],
             },
        ]
        self.cntxt = RequestContext(user_id='demo',
                                    project_id='abcd',
                                    auth_token='efgh',
                                    service_catalog=service_catalog)
        self.trove_client = client_factory.ClientFactory.create_client(
            "trove", self.cntxt)
        self.checkpoint = FakeCheckpoint()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            constants.DATABASE_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         database_backup_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            constants.DATABASE_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         database_backup_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            constants.DATABASE_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         database_backup_plugin_schemas.SAVED_INFO_SCHEMA)

    @mock.patch('karbor.services.protection.protection_plugins.database.'
                'database_backup_plugin.utils.status_poll')
    @mock.patch('karbor.services.protection.clients.trove.create')
    def test_create_backup(self, mock_trove_create, mock_status_poll):
        resource = Resource(id="123",
                            type=constants.DATABASE_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.update_object = mock.MagicMock()

        protect_operation = self.plugin.get_protect_operation(resource)
        mock_trove_create.return_value = self.trove_client

        self.trove_client.instances.get = mock.MagicMock()
        self.trove_client.instances.return_value = Database(
            status="ACTIVE"
        )
        fake_bank_section.update_object = mock.MagicMock()
        self.trove_client.backups.create = mock.MagicMock()
        self.trove_client.backups.create.return_value = Backup(
            id="1234",
            status="COMPLETED"
        )
        self.trove_client.backups.get = mock.MagicMock()
        self.trove_client.backups.get.return_value = Backup(
            id="1234",
            status="COMPLETED"
        )
        mock_status_poll.return_value = True
        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})

    @mock.patch('karbor.services.protection.protection_plugins.database.'
                'database_backup_plugin.utils.status_poll')
    @mock.patch('karbor.services.protection.clients.trove.create')
    def test_delete_backup(self, mock_trove_create, mock_status_poll):
        resource = Resource(id="123",
                            type=constants.DATABASE_RESOURCE_TYPE,
                            name='fake')
        mock_trove_create.return_value = self.trove_client
        self.trove_client.backups.get = mock.MagicMock()
        self.trove_client.backups.get.return_value = Backup(
            id="1234",
            status="COMPLETED"
        )
        self.trove_client.backups.delete = mock.MagicMock()

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = {
            "backup_id": "1234"}

        mock_status_poll.return_value = True
        delete_operation = self.plugin.get_delete_operation(resource)
        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    @mock.patch('karbor.services.protection.protection_plugins.utils.'
                'update_resource_verify_result')
    @mock.patch('karbor.services.protection.clients.trove.create')
    def test_verify_backup(self, mock_trove_create, mock_update_verify):
        resource = Resource(id="123",
                            type=constants.DATABASE_RESOURCE_TYPE,
                            name='fake')
        mock_trove_create.return_value = self.trove_client
        self.trove_client.backups.get = mock.MagicMock()
        self.trove_client.backups.get.return_value = Backup(
            id="1234",
            status="COMPLETED"
        )

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = {
            "backup_id": "1234"}

        verify_operation = self.plugin.get_verify_operation(resource)
        call_hooks(verify_operation, self.checkpoint, resource, self.cntxt,
                   {})
        mock_update_verify.assert_called_with(
            None, resource.type, resource.id, 'available')

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.DATABASE_RESOURCE_TYPE])
