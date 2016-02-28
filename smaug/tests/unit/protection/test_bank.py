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

import six

from smaug.tests import base

from smaug.services.protection.bank_plugin import Bank
from smaug.services.protection.bank_plugin import BankPlugin
from smaug.services.protection.bank_plugin import BankSection


class _InMemoryBankPlugin(BankPlugin):
    def __init__(self):
        self._data = OrderedDict()

    def create_object(self, key, value):
        if self._data.setdefault(key, value) != value:
            raise KeyError("Object with this key already exists")

    def update_object(self, key, value):
        self._data[key] = value

    def get_object(self, key):
        return self._data[key]

    def list_objects(self, prefix=None, limit=None, marker=None):
        marker_found = marker is None
        for key in six.iterkeys(self._data):
            if marker is not True and key != marker:
                if marker_found:
                    if prefix is None or key.startswith(prefix):
                        if limit is not None:
                            limit = limit - 1
                            if limit < 0:
                                return

                        yield key

            else:
                marker_found = True

    def delete_object(self, key):
        del self._data[key]


class BankSectionTest(base.TestCase):
    def _create_test_bank(self):
        return Bank(_InMemoryBankPlugin())

    def test_empty_key(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=True)
        self.assertRaises(RuntimeError, section.create_object, "", "value")
        self.assertRaises(RuntimeError, section.create_object, None, "value")

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
        expected_result = ["/a", "/b", "/c"]
        self.assertEqual(list(section.list_objects("/")), expected_result)
        self.assertEqual(list(section.list_objects("///")), expected_result)
        self.assertEqual(list(section.list_objects(None)), expected_result)
        self.assertEqual(
            list(section.list_objects("/", limit=2)),
            expected_result[:2],
        )
        self.assertEqual(
            list(section.list_objects("/", limit=2, marker="/b")),
            expected_result[2:4],
        )

    def test_read_only(self):
        bank = self._create_test_bank()
        section = BankSection(bank, "/prefix", is_writable=False)
        self.assertRaises(
            RuntimeError,
            section.create_object,
            "object",
            "value",
        )
        bank.create_object("/prefix/object", "value")
        self.assertRaises(
            RuntimeError,
            section.update_object,
            "object",
            "value",
        )
        self.assertRaises(
            RuntimeError,
            section.delete_object,
            "object",
        )
