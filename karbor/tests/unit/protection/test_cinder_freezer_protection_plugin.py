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
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection import client_factory
from karbor.services.protection.protection_plugins.volume import \
    volume_freezer_plugin_schemas
from karbor.services.protection.protection_plugins.volume.\
    volume_freezer_plugin import FreezerProtectionPlugin

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

Job = collections.namedtuple(
    "Job",
    ["job_schedule"]
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
        self.id = "fake_id"

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class VolumeFreezerProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(VolumeFreezerProtectionPluginTest, self).setUp()

        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='freezer_protection_plugin',
            poll_interval=0,
        )

        self.plugin = FreezerProtectionPlugin(plugin_config)
        self._public_url = 'http://127.0.0.1/v2.0'
        cfg.CONF.set_default('freezer_endpoint',
                             self._public_url,
                             'freezer_client')
        # due to freezer client bug, auth_uri should be specified
        cfg.CONF.set_default('auth_uri',
                             'http://127.0.0.1/v2.0',
                             'freezer_client')
        self.cntxt = RequestContext(user_id='demo',
                                    project_id='fake_project_id',
                                    auth_token='fake_token')

        self.freezer_client = client_factory.ClientFactory.create_client(
            'freezer', self.cntxt
        )
        self.checkpoint = FakeCheckpoint()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            constants.VOLUME_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         volume_freezer_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            constants.VOLUME_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         volume_freezer_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            constants.VOLUME_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         volume_freezer_plugin_schemas.SAVED_INFO_SCHEMA)

    @mock.patch('karbor.services.protection.protection_plugins.volume.'
                'volume_freezer_plugin.utils.status_poll')
    @mock.patch('karbor.services.protection.clients.freezer.create')
    def test_create_backup(self, mock_freezer_create, mock_status_poll):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.update_object = mock.MagicMock()
        protect_operation = self.plugin.get_protect_operation(resource)
        mock_freezer_create.return_value = self.freezer_client
        mock_status_poll.return_value = True

        self.freezer_client.clients.list = mock.MagicMock()
        self.freezer_client.clients.list.return_value = [
            {
                'client_id': 'fake_client_id'
            }
        ]

        self.freezer_client.jobs.create = mock.MagicMock()
        self.freezer_client.jobs.create.return_value = "123"
        self.freezer_client.jobs.start_job = mock.MagicMock()
        self.freezer_client.jobs.get = mock.MagicMock()
        self.freezer_client.jobs.get.return_value = {
            'job_actions': []
        }
        self.freezer_client.jobs.delete = mock.MagicMock()
        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})

    @mock.patch('karbor.services.protection.protection_plugins.volume.'
                'volume_freezer_plugin.utils.status_poll')
    @mock.patch('karbor.services.protection.clients.freezer.create')
    def test_delete_backup(self, mock_freezer_create, mock_status_poll):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name='fake')
        delete_operation = self.plugin.get_delete_operation(resource)
        fake_bank_section.update_object = mock.MagicMock()
        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = {
            'job_info': {
                'description': '123',
                'job_actions': [{
                    'freezer_action': {
                        'backup_name': 'test',
                        'action': 'backup',
                        'mode': 'cinder',
                        'cinder_vol_id': 'test',
                        'storage': 'swift',
                        'container': 'karbor/123'
                    }
                }]
            }
        }
        mock_freezer_create.return_value = self.freezer_client
        mock_status_poll.return_value = True
        self.freezer_client.jobs.create = mock.MagicMock()
        self.freezer_client.jobs.create.return_value = '321'
        self.freezer_client.jobs.start_job = mock.MagicMock()
        self.freezer_client.jobs.get = mock.MagicMock()
        self.freezer_client.jobs.get.return_value = {
            'job_actions': []
        }
        self.freezer_client.jobs.delete = mock.MagicMock()
        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.VOLUME_RESOURCE_TYPE])
