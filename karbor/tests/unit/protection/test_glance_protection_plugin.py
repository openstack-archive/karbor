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
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection.protection_plugins. \
    image.image_protection_plugin import GlanceProtectionPlugin
from karbor.services.protection.protection_plugins.image \
    import image_plugin_schemas
from karbor.tests import base
import mock
from oslo_config import cfg


class FakeBankPlugin(BankPlugin):
    def create_object(self, key, value):
        return

    def update_object(self, key, value):
        return

    def get_object(self, key):
        return

    def list_objects(self, prefix=None, limit=None, marker=None):
        return

    def delete_object(self, key):
        return

    def get_owner_id(self):
        return


fake_bank = Bank(FakeBankPlugin())
fake_bank_section = BankSection(bank=fake_bank, prefix="fake")

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


class CheckpointCollection(object):
    def __init__(self):
        self.bank_section = fake_bank_section

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class GlanceProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(GlanceProtectionPluginTest, self).setUp()
        self.plugin = GlanceProtectionPlugin()
        cfg.CONF.set_default('glance_endpoint',
                             'http://127.0.0.1:9292',
                             'glance_client')

        self.cntxt = RequestContext(user_id='admin',
                                    project_id='abcd',
                                    auth_token='efgh')
        self.glance_client = ClientFactory.create_client("glance", self.cntxt)
        self.checkpoint = CheckpointCollection()

    def test_get_resource_stats(self):
        fake_resource_id = "123"

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = \
            constants.RESOURCE_STATUS_PROTECTING
        status = self.plugin.get_resource_stats(self.checkpoint,
                                                fake_resource_id)
        self.assertEqual(status, constants.RESOURCE_STATUS_PROTECTING)

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

    def test_create_backup(self):
        resource = Resource(id="123",
                            type=constants.IMAGE_RESOURCE_TYPE,
                            name='fake')
        resource_node = ResourceNode(value=resource,
                                     child_nodes=[])

        fake_bank_section.create_object = mock.MagicMock()

        self.plugin._glance_client = mock.MagicMock()
        self.plugin._glance_client.return_value = self.glance_client

        self.glance_client.images.get = mock.MagicMock()
        self.glance_client.images.return_value = Image(
            disk_format="",
            container_format="",
            status="active"
        )

        fake_bank_section.update_object = mock.MagicMock()

        self.glance_client.images.data = mock.MagicMock()
        self.glance_client.images.data.return_value = "image-data"

        self.plugin.create_backup(self.cntxt, self.checkpoint,
                                  node=resource_node)

    def test_delete_backup(self):
        resource = Resource(id="123",
                            type=constants.IMAGE_RESOURCE_TYPE,
                            name='fake')
        resource_node = ResourceNode(value=resource,
                                     child_nodes=[])

        fake_bank_section.list_objects = mock.MagicMock()
        fake_bank_section.list_objects.return_value = ["data_1", "data_2"]
        fake_bank_section.delete_object = mock.MagicMock()
        self.plugin.delete_backup(self.cntxt, self.checkpoint,
                                  node=resource_node)

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.IMAGE_RESOURCE_TYPE])
