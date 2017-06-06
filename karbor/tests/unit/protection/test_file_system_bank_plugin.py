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

import os
import tempfile

from oslo_config import cfg
from oslo_config import fixture
from oslo_utils import importutils

from karbor import exception
from karbor.tests import base


class FileSystemBankPluginTest(base.TestCase):
    def setUp(self):
        super(FileSystemBankPluginTest, self).setUp()

        import_str = (
            "karbor.services.protection.bank_plugins."
            "file_system_bank_plugin.FileSystemBankPlugin"
        )
        plugin_config = cfg.ConfigOpts()
        plugin_config_fixture = self.useFixture(fixture.Config(plugin_config))
        plugin_config_fixture.load_raw_values(
            group='file_system_bank_plugin',
            file_system_bank_path=tempfile.mkdtemp(),
        )
        fs_bank_plugin_cls = importutils.import_class(
            import_str=import_str)
        self.fs_bank_plugin = fs_bank_plugin_cls(plugin_config)

    def test_delete_object(self):
        self.fs_bank_plugin.update_object("/key", "value")
        self.fs_bank_plugin.delete_object("/key")
        object_file = (
            self.fs_bank_plugin.object_container_path + "/key")
        self.assertEqual(os.path.isfile(object_file), False)

    def test_get_object(self):
        self.fs_bank_plugin.update_object("/key", "value")
        value = self.fs_bank_plugin.get_object("/key")
        self.assertEqual(value, "value")

    def test_list_objects(self):
        self.fs_bank_plugin.update_object("/list/key-1", "value-1")
        self.fs_bank_plugin.update_object("/list/key-2", "value-2")
        objects = self.fs_bank_plugin.list_objects(prefix="/list")
        self.assertEqual(len(objects), 2)
        self.assertIn('key-1', objects)
        self.assertIn('key-2', objects)

    def test_update_object(self):
        self.fs_bank_plugin.update_object("/key-1", "value-1")
        self.fs_bank_plugin.update_object("/key-1", "value-2")
        object_file = (
            self.fs_bank_plugin.object_container_path + "/key-1")
        with open(object_file, "r") as f:
            contents = f.read()
        self.assertEqual(contents, "value-2")

    def test_update_object_with_invaild_path(self):
        self.assertRaises(exception.InvalidInput,
                          self.fs_bank_plugin.update_object,
                          "../../../../../../../etc/shadow",
                          "value-1")

    def test_create_get_dict_object(self):
        self.fs_bank_plugin.update_object("/index.json",
                                          {"key": "value"})
        value = self.fs_bank_plugin.get_object(
            "/index.json")
        self.assertEqual(value, {"key": "value"})
