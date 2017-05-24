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
from karbor.services.protection.protection_plugins. \
    image.image_protection_plugin import GlanceProtectionPlugin
from karbor.services.protection.protection_plugins.image \
    import image_plugin_schemas
from karbor.tests import base
import mock
from oslo_config import cfg
from oslo_config import fixture


class FakeBankPlugin(BankPlugin):
    def update_object(self, key, value):
        return

    def get_object(self, key):
        return

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        return

    def delete_object(self, key):
        return

    def get_owner_id(self):
        return


fake_bank = Bank(FakeBankPlugin())
fake_bank_section = BankSection(bank=fake_bank, section="fake")

ResourceNode = collections.namedtuple(
    "ResourceNode",
    ["value",
     "child_nodes"]
)


Image = collections.namedtuple(
    "Image",
    ["disk_format",
     "container_format",
     "status"]
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


class CheckpointCollection(object):
    def __init__(self):
        super(CheckpointCollection, self).__init__()
        self.bank_section = fake_bank_section

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class GlanceProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(GlanceProtectionPluginTest, self).setUp()

        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='image_backup_plugin',
            poll_interval=0,
        )
        plugin_config_fixture.load_raw_values(
            group='image_backup_plugin',
            backup_image_object_size=65536,
        )
        self.plugin = GlanceProtectionPlugin(plugin_config)
        cfg.CONF.set_default('glance_endpoint',
                             'http://127.0.0.1:9292',
                             'glance_client')

        self.cntxt = RequestContext(user_id='demo',
                                    project_id='abcd',
                                    auth_token='efgh')
        self.glance_client = client_factory.ClientFactory.create_client(
            "glance", self.cntxt)
        self.checkpoint = CheckpointCollection()

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            constants.IMAGE_RESOURCE_TYPE)
        self.assertEqual(options_schema, image_plugin_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            constants.IMAGE_RESOURCE_TYPE)
        self.assertEqual(options_schema, image_plugin_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            constants.IMAGE_RESOURCE_TYPE)
        self.assertEqual(options_schema,
                         image_plugin_schemas.SAVED_INFO_SCHEMA)

    @mock.patch('karbor.services.protection.protection_plugins.image.'
                'image_protection_plugin.utils.status_poll')
    @mock.patch('karbor.services.protection.clients.glance.create')
    def test_create_backup(self, mock_glance_create, mock_status_poll):
        resource = Resource(id="123",
                            type=constants.IMAGE_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.update_object = mock.MagicMock()

        protect_operation = self.plugin.get_protect_operation(resource)
        mock_glance_create.return_value = self.glance_client

        self.glance_client.images.get = mock.MagicMock()
        self.glance_client.images.return_value = Image(
            disk_format="",
            container_format="",
            status="active"
        )

        fake_bank_section.update_object = mock.MagicMock()
        self.glance_client.images.data = mock.MagicMock()
        self.glance_client.images.data.return_value = []
        mock_status_poll.return_value = True
        call_hooks(protect_operation, self.checkpoint, resource, self.cntxt,
                   {})

    def test_delete_backup(self):
        resource = Resource(id="123",
                            type=constants.IMAGE_RESOURCE_TYPE,
                            name='fake')

        fake_bank_section.list_objects = mock.MagicMock()
        fake_bank_section.list_objects.return_value = ["data_1", "data_2"]
        fake_bank_section.delete_object = mock.MagicMock()
        delete_operation = self.plugin.get_delete_operation(resource)
        call_hooks(delete_operation, self.checkpoint, resource, self.cntxt,
                   {})

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.IMAGE_RESOURCE_TYPE])
