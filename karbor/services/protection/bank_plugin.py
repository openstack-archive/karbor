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

import abc
import os
import six

from oslo_config import cfg
from oslo_log import log as logging

from karbor import exception

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class LeasePlugin(object):
    @abc.abstractmethod
    def acquire_lease(self):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def renew_lease(self):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def check_lease_validity(self):
        # TODO(wangliuan)
        pass


@six.add_metaclass(abc.ABCMeta)
class BankPlugin(object):
    def __init__(self, config=None):
        self._config = config

    @abc.abstractmethod
    def create_object(self, key, value):
        return

    @abc.abstractmethod
    def update_object(self, key, value):
        return

    @abc.abstractmethod
    def get_object(self, key):
        return

    @abc.abstractmethod
    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        return

    @abc.abstractmethod
    def delete_object(self, key):
        return

    @abc.abstractmethod
    def get_owner_id(self):
        return


class Bank(object):
    def __init__(self, plugin):
        self._plugin = plugin

    def _normalize_key(self, key):
        """Normalizes the key

        To prevent small errors regarding path joining we define that
        banks use path normalization similar to file systems.

        This means that all paths are relative to '/' and that
        '/path//dir' == '/path/dir'
        """
        key = os.path.normpath(key)
        if not key.startswith("/"):
            key = "/" + key

        return key

    def create_object(self, key, value):
        return self._plugin.create_object(self._normalize_key(key), value)

    def update_object(self, key, value):
        return self._plugin.update_object(self._normalize_key(key), value)

    def get_object(self, key):
        return self._plugin.get_object(self._normalize_key(key))

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        if not prefix:
            prefix = "/"

        return self._plugin.list_objects(
            prefix=self._normalize_key(prefix) + "/",
            limit=limit,
            marker=marker,
            sort_dir=sort_dir
        )

    def delete_object(self, key):
        return self._plugin.delete_object(self._normalize_key(key))

    def get_sub_section(self, prefix, is_writable=True):
        return BankSection(self, prefix, is_writable)

    def get_owner_id(self):
        return self._plugin.get_owner_id()


class BankSection(object):
    """Bank Section compartmentalizes a section of a bank.

    Bank section is used when an object wants to pass a section of
    a bank to another entity and make sure it is only capable of
    accessing part of it.
    """
    def __init__(self, bank, prefix, is_writable=True):
        self._validate_key(prefix)

        self._bank = bank
        self._prefix = os.path.normpath(prefix or "/")
        if not self._prefix.startswith("/"):
            prefix = "/" + prefix

        self._is_writable = is_writable

    def get_sub_section(self, prefix, is_writable=True):
        if is_writable and not self._is_writable:
            raise exception.BankReadonlyViolation()

        return BankSection(self._bank, self._prefix + '/' + prefix,
                           self._is_writable)

    @property
    def is_writable(self):
        return self._is_writable

    @staticmethod
    def _validate_key(key):
        if not key:
            raise exception.InvalidParameterValue(
                err='Invalid parameter: empty'
            )
        if key.find('..') != -1:
            raise exception.InvalidParameterValue(
                err='Invalid parameter: must not contain ".."'
            )

    def _prepend_prefix(self, key):
        self._validate_key(key)

        if not key.startswith("/"):
            key = "/" + key

        return "%s%s" % (self._prefix, key)

    def _validate_writable(self):
        if not self.is_writable:
            raise exception.BankReadonlyViolation()

    def create_object(self, key, value):
        self._validate_writable()
        return self._bank.create_object(
            self._prepend_prefix(key),
            value,
        )

    def update_object(self, key, value):
        self._validate_writable()
        return self._bank.update_object(
            self._prepend_prefix(key),
            value,
        )

    def get_object(self, key):
        return self._bank.get_object(
            self._prepend_prefix(key),
        )

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        if not prefix:
            prefix = self._prefix
        else:
            prefix = self._prepend_prefix(prefix)

        if marker is not None:
            marker = self._prepend_prefix(marker)

        return [key[len(self._prefix) + 1:]
                for key in self._bank.list_objects(
                    prefix,
                    limit,
                    marker,
                    sort_dir
                    )
                ]

    def delete_object(self, key):
        self._validate_writable()
        return self._bank.delete_object(
            self._prepend_prefix(key),
        )

    @property
    def bank(self):
        return self._bank
