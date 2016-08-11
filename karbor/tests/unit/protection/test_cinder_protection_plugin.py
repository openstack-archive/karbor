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
import datetime
from karbor.common import constants
from karbor.context import RequestContext
from karbor.resource import Resource
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection.protection_plugins.volume. \
    cinder_protection_plugin import CinderProtectionPlugin
from karbor.services.protection.protection_plugins.volume \
    import volume_plugin_cinder_schemas as cinder_schemas
from karbor.services.protection.restore_heat import HeatTemplate
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


class FakeCheckpoint(object):
    def __init__(self):
        self.bank_section = fake_bank_section
        self.id = "fake_id"

    def get_resource_bank_section(self, resource_id):
        return self.bank_section


class CinderProtectionPluginTest(base.TestCase):
    def setUp(self):
        super(CinderProtectionPluginTest, self).setUp()
        self.plugin = CinderProtectionPlugin()
        cfg.CONF.set_default('cinder_endpoint',
                             'http://127.0.0.1:8776/v2',
                             'cinder_client')

        self.cntxt = RequestContext(user_id='admin',
                                    project_id='abcd',
                                    auth_token='efgh')
        self.cinder_client = ClientFactory.create_client("cinder", self.cntxt)
        self.checkpoint = FakeCheckpoint()

    def test_get_resource_stats(self):
        fake_resource_id = "123"
        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = \
            constants.RESOURCE_STATUS_AVAILABLE
        status = self.plugin.get_resource_stats(self.checkpoint,
                                                fake_resource_id)
        self.assertEqual(status, constants.RESOURCE_STATUS_AVAILABLE)

    def test_get_options_schema(self):
        options_schema = self.plugin.get_options_schema(
            'OS::Cinder::Volume')
        self.assertEqual(options_schema, cinder_schemas.OPTIONS_SCHEMA)

    def test_get_restore_schema(self):
        options_schema = self.plugin.get_restore_schema(
            'OS::Cinder::Volume')
        self.assertEqual(options_schema, cinder_schemas.RESTORE_SCHEMA)

    def test_get_saved_info_schema(self):
        options_schema = self.plugin.get_saved_info_schema(
            'OS::Cinder::Volume')
        self.assertEqual(options_schema,
                         cinder_schemas.SAVED_INFO_SCHEMA)

    def test_create_backup(self):
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name="test")
        resource_node = ResourceNode(value=resource,
                                     child_nodes=[])

        fake_bank_section.create_object = mock.MagicMock()

        self.plugin._cinder_client = mock.MagicMock()
        self.plugin._cinder_client.return_value = self.cinder_client

        self.cinder_client.backups.create = mock.MagicMock()
        self.cinder_client.backups.return_value = "456"

        fake_bank_section.create_object = mock.MagicMock()
        # fake_bank_section.update_object = mock.MagicMock()

        self.plugin.create_backup(self.cntxt, self.checkpoint,
                                  node=resource_node)

    def test_delete_backup(self):
        resource = Resource(id="123",
                            type=constants.SERVER_RESOURCE_TYPE,
                            name="test")
        resource_node = ResourceNode(value=resource,
                                     child_nodes=[])

        fake_bank_section.update_object = mock.MagicMock()

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = {
            "backup_id": "456"
        }

        self.plugin._cinder_client = mock.MagicMock()
        self.plugin._cinder_client.return_value = self.cinder_client
        self.cinder_client.backups.delete = mock.MagicMock()

        fake_bank_section.delete_object = mock.MagicMock()

        self.plugin.delete_backup(self.cntxt, self.checkpoint,
                                  node=resource_node)

    def test_restore_backup(self):
        heat_template = HeatTemplate()
        resource = Resource(id="123",
                            type=constants.VOLUME_RESOURCE_TYPE,
                            name="fake")
        resource_node = ResourceNode(value=resource,
                                     child_nodes=[])
        resource_definition = {"backup_id": "456"}
        kwargs = {"node": resource_node,
                  "heat_template": heat_template,
                  "restore_name": "karbor restore volume",
                  "restore_description": "karbor restore"}

        fake_bank_section.get_object = mock.MagicMock()
        fake_bank_section.get_object.return_value = resource_definition

        self.plugin.restore_backup(self.cntxt, self.checkpoint,
                                   **kwargs)
        self.assertEqual(1, len(heat_template._resources))

        heat_resource_id = heat_template._original_id_resource_map["123"]
        template_dict = {
            "heat_template_version": str(datetime.date(2015, 10, 15)),
            "description": "karbor restore template",
            "resources": {
                heat_resource_id: {
                    "type": "OS::Cinder::Volume",
                    "properties": {
                        "description": "karbor restore",
                        "backup_id": "456",
                        "name": "karbor restore volume",
                    }
                }
            }
        }
        self.assertEqual(template_dict, heat_template.to_dict())

    def test_get_supported_resources_types(self):
        types = self.plugin.get_supported_resources_types()
        self.assertEqual(types,
                         [constants.VOLUME_RESOURCE_TYPE])

    def tearDown(self):
        super(CinderProtectionPluginTest, self).tearDown()
