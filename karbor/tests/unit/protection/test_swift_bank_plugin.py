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

from karbor.services.protection.clients import swift
from karbor.tests import base
from karbor.tests.unit.protection.fake_swift_client import FakeSwiftClient
import math
import mock
import os
from oslo_config import cfg
from oslo_utils import importutils
import time

CONF = cfg.CONF


class FakeConf(object):
    def __init__(self):
        super(FakeConf, self).__init__()
        self.lease_expire_window = 600
        self.lease_renew_window = 120
        self.lease_validity_window = 100


class SwiftBankPluginTest(base.TestCase):
    def setUp(self):
        super(SwiftBankPluginTest, self).setUp()
        self.conf = FakeConf()
        self.fake_connection = FakeSwiftClient.connection()
        swift.create = mock.MagicMock()
        swift.create.return_value = self.fake_connection
        import_str = (
            "karbor.services.protection.bank_plugins."
            "swift_bank_plugin.SwiftBankPlugin"
        )
        self.object_container = "objects"
        swift_bank_plugin_cls = importutils.import_class(
            import_str=import_str)

        self.swift_bank_plugin = swift_bank_plugin_cls(CONF, None)

    def test_acquire_lease(self):
        self.swift_bank_plugin.acquire_lease()
        expire_time = math.floor(time.time()) + self.conf.lease_expire_window
        self.assertEqual(self.swift_bank_plugin.lease_expire_time, expire_time)

    def test_renew_lease(self):
        self.swift_bank_plugin.acquire_lease()
        expire_time = math.floor(time.time()) + self.conf.lease_expire_window
        self.assertEqual(self.swift_bank_plugin.lease_expire_time, expire_time)
        time.sleep(5)
        self.swift_bank_plugin.acquire_lease()
        expire_time = math.floor(time.time()) + self.conf.lease_expire_window
        self.assertEqual(self.swift_bank_plugin.lease_expire_time, expire_time)

    def test_check_lease_validity(self):
        self.swift_bank_plugin.acquire_lease()
        expire_time = math.floor(time.time()) + self.conf.lease_expire_window
        self.assertEqual(self.swift_bank_plugin.lease_expire_time, expire_time)
        is_valid = self.swift_bank_plugin.check_lease_validity()
        self.assertEqual(is_valid, True)

    def test_delete_object(self):
        self.swift_bank_plugin.update_object("key", "value")
        self.swift_bank_plugin.delete_object("key")
        object_file = os.path.join(self.fake_connection.swiftdir,
                                   "karbor",
                                   "key")
        self.assertEqual(os.path.isfile(object_file), False)

    def test_get_object(self):
        self.swift_bank_plugin.update_object("key", "value")
        value = self.swift_bank_plugin.get_object("key")
        self.assertEqual(value, "value")

    def test_list_objects(self):
        self.swift_bank_plugin.update_object("key-1", "value-1")
        self.swift_bank_plugin.update_object("key-2", "value-2")
        objects = self.swift_bank_plugin.list_objects(prefix=None)
        self.assertEqual(len(objects), 2)

    def test_update_object(self):
        self.swift_bank_plugin.update_object("key-1", "value-1")
        self.swift_bank_plugin.update_object("key-1", "value-2")
        object_file = os.path.join(self.fake_connection.swiftdir,
                                   "karbor",
                                   "key-1")
        with open(object_file, "r") as f:
            contents = f.read()
        self.assertEqual(contents, "value-2")

    def test_create_get_dict_object(self):
        self.swift_bank_plugin.update_object("dict_object", {"key": "value"})
        value = self.swift_bank_plugin.get_object("dict_object")
        self.assertEqual(value, {"key": "value"})
