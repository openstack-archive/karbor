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
import six
from uuid import uuid4 as uuid

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

    def create_object(self, key, value):
        self._data[key] = value

    def update_object(self, key, value):
        self._data[key] = value

    def get_object(self, key):
        return deepcopy(self._data[key])

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
        return str(uuid())


class _InMemoryLeasePlugin(LeasePlugin):

    def acquire_lease(self):
        pass

    def renew_lease(self):
        pass

    def check_lease_validity(self):
        return True


class BankSectionTest(base.TestCase):
    def _create_test_bank(self):
        return Bank(_InMemoryBankPlugin())

    def test_empty_key(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        self.assertRaises(
            exception.InvalidParameterValue,
            section.create_object,
            "",
            "value",
        )
        self.assertRaises(
            exception.InvalidParameterValue,
            section.create_object,
            None,
            "value",
        )

    def test_delete_object(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        bank.create_object("/prefix/a", "value")
        bank.create_object("/prefix/b", "value")
        bank.create_object("/prefix/c", "value")
        section.delete_object("a")
        section.delete_object("/b")
        section.delete_object("//c")

    def test_list_objects(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        bank.create_object("/prefix/a", "value")
        bank.create_object("/prefixd", "value")  # Should not appear
        section.create_object("/b", "value")
        section.create_object("c", "value")
        expected_result = ["a", "b", "c"]
        self.assertEqual(list(section.list_objects("/")), expected_result)
        self.assertEqual(list(section.list_objects("///")), expected_result)
        self.assertEqual(list(section.list_objects(None)), expected_result)
        self.assertEqual(
            list(section.list_objects("/", limit=2)),
            expected_result[:2],
        )
        self.assertEqual(
            list(section.list_objects("/", limit=2, marker="b")),
            expected_result[2:4],
        )

    def test_read_only(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=False)
        self.assertRaises(
            exception.BankReadonlyViolation,
            section.create_object,
            "object",
            "value",
        )
        bank.create_object("/prefix/object", "value")
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
            section.create_object,
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

    def test_nested_sections(self):
        bank = self._create_test_bank()
        top_section = BankSection(bank, "/top")
        mid_section = top_section.get_sub_section("/mid")
        bottom_section = mid_section.get_sub_section("/bottom")
        bottom_section.create_object("key", "value")
        self.assertEqual(bank.get_object("/top/mid/bottom/key"), "value")

    def test_nested_sections_read_only(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/top", is_writable=False)
        self.assertRaises(
            exception.BankReadonlyViolation,
            section.get_sub_section,
            "/mid",
            is_writable=True,
        )
