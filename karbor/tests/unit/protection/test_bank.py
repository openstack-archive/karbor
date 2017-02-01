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

from collections import OrderedDict
from copy import deepcopy
from oslo_utils import uuidutils
import six

from karbor import exception
from karbor.services.protection.bank_plugin import Bank
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import BankSection
from karbor.services.protection.bank_plugin import LeasePlugin
from karbor.tests import base


class _InMemoryBankPlugin(BankPlugin):
    def __init__(self, config=None):
        super(_InMemoryBankPlugin, self).__init__(config)
        self._data = OrderedDict()

    def update_object(self, key, value):
        self._data[key] = value

    def get_object(self, key):
        try:
            return deepcopy(self._data[key])
        except KeyError:
            raise exception.BankGetObjectFailed('no such object')

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        marker_found = marker is None
        for key in six.iterkeys(self._data):
            if marker is not True and key != marker:
                if marker_found:
                    if prefix is None or key.startswith(prefix):
                        if limit is not None:
                            limit -= 1
                            if limit < 0:
                                return
                        yield key
            else:
                marker_found = True

    def delete_object(self, key):
        del self._data[key]

    def get_owner_id(self):
        return uuidutils.generate_uuid()


class _InMemoryLeasePlugin(LeasePlugin):

    def acquire_lease(self):
        pass

    def renew_lease(self):
        pass

    def check_lease_validity(self):
        return True


class BankSectionTest(base.TestCase):
    INVALID_PATHS = (
        '/',
        '/a$',
        '/path/',
        '/path/path/',
        'space space',
        '/path/../dots/',
        '/,',
    )

    VALID_PATHS = (
        '/key',
        '/top/key',
        '/top/middle/bottom/key',
        '/all_kinds/of-char.acters/@path1',
    )

    def _create_test_bank(self):
        return Bank(_InMemoryBankPlugin())

    def test_empty_key(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        self.assertRaises(
            exception.InvalidParameterValue,
            section.update_object,
            "",
            "value",
        )
        self.assertRaises(
            exception.InvalidParameterValue,
            section.update_object,
            None,
            "value",
        )

    def test_update_invalid_object(self):
        bank = self._create_test_bank()
        for path in self.INVALID_PATHS:
            self.assertRaises(
                exception.InvalidParameterValue,
                bank.update_object,
                path,
                "value",
            )

    def test_get_invalid_object(self):
        bank = self._create_test_bank()
        for path in self.INVALID_PATHS:
            self.assertRaises(
                exception.InvalidParameterValue,
                bank.get_object,
                path,
            )

    def test_valid_object(self):
        value1 = 'value1'
        value2 = 'value2'
        bank = self._create_test_bank()
        for path in self.VALID_PATHS:
            bank.update_object(path, value1)
            bank.update_object(path, value2)
            res = bank.get_object(path)
            self.assertEqual(res, value2)
            bank.delete_object(path)
            self.assertRaises(
                exception.BankGetObjectFailed,
                bank.get_object,
                path,
            )

    def test_delete_object(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        bank.update_object("/prefix/a", "value")
        bank.update_object("/prefix/b", "value")
        bank.update_object("/prefix/c", "value")
        section.delete_object("a")
        section.delete_object("/b")
        section.delete_object("//c")

    def test_list_objects(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        bank.update_object("/prefix/KeyA", "value")
        bank.update_object("/prefix", "value")
        bank.update_object("/prefixKeyD", "value")  # Should not appear
        section.update_object("/KeyB", "value")
        section.update_object("KeyC", "value")
        expected_result = ["KeyA", "KeyB", "KeyC"]
        self.assertEqual(list(section.list_objects("/")), expected_result)
        self.assertEqual(list(section.list_objects("///")), expected_result)
        self.assertEqual(list(section.list_objects(None)), expected_result)
        self.assertEqual(list(section.list_objects("Key")), expected_result)
        self.assertEqual(
            list(section.list_objects("/", limit=2)),
            expected_result[:2],
        )
        self.assertEqual(
            list(section.list_objects("/", limit=2, marker="KeyB")),
            expected_result[2:4],
        )

    def test_read_only(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=False)
        self.assertRaises(
            exception.BankReadonlyViolation,
            section.update_object,
            "object",
            "value",
        )
        bank.update_object("/prefix/object", "value")
        self.assertRaises(
            exception.BankReadonlyViolation,
            section.update_object,
            "object",
            "value",
        )
        self.assertRaises(
            exception.BankReadonlyViolation,
            section.delete_object,
            "object",
        )

    def test_double_dot_key(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix")
        self.assertRaises(
            exception.InvalidParameterValue,
            section.update_object,
            "/../../",
            "",
        )

    def test_double_dot_section_prefix(self):
        bank = self._create_test_bank()
        self.assertRaises(
            exception.InvalidParameterValue,
            BankSection,
            bank,
            '/../../',
        )

    def test_nested_sections_get(self):
        bank = self._create_test_bank()
        top_section = BankSection(bank, "/top")
        mid_section = top_section.get_sub_section("/mid")
        bottom_section = mid_section.get_sub_section("/bottom")
        bottom_section.update_object("key", "value")
        self.assertEqual(bank.get_object("/top/mid/bottom/key"), "value")
        self.assertEqual(bottom_section.get_object("key"), "value")

    def test_nested_sections_list(self):
        bank = self._create_test_bank()
        top_section = BankSection(bank, "/top")
        mid_section = top_section.get_sub_section("/mid")
        bottom_section = mid_section.get_sub_section("/bottom")
        keys = ["KeyA", "KeyB", "KeyC"]
        for key in keys:
            bottom_section.update_object(key, "value")

        list_result = set(bottom_section.list_objects(prefix="Key"))
        self.assertEqual(list_result, set(keys))
        self.assertEqual(
            list(bottom_section.list_objects("/", limit=2)),
            keys[:2],
        )
        self.assertEqual(
            list(bottom_section.list_objects("/", limit=2, marker="KeyB")),
            keys[2:4],
        )

    def test_nested_sections_read_only(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/top", is_writable=False)
        self.assertRaises(
            exception.BankReadonlyViolation,
            section.get_sub_section,
            "/mid",
            is_writable=True,
        )
