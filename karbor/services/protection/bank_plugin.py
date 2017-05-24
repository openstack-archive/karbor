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
import re
import six

from karbor import exception
from karbor.i18n import _


@six.add_metaclass(abc.ABCMeta)
class LeasePlugin(object):
    @abc.abstractmethod
    def acquire_lease(self):
        pass

    @abc.abstractmethod
    def renew_lease(self):
        pass

    @abc.abstractmethod
    def check_lease_validity(self):
        pass


@six.add_metaclass(abc.ABCMeta)
class BankPlugin(object):
    def __init__(self, config=None):
        super(BankPlugin, self).__init__()
        self._config = config

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


def validate_key(key):
    pass


def validate_dir(key):
    pass


class Bank(object):
    _KEY_VALIDATION = re.compile('^[A-Za-z0-9/_.\-@]+(?<!/)$')
    _KEY_DOT_VALIDATION = re.compile('/\.{1,2}(/|$)')

    def __init__(self, plugin):
        super(Bank, self).__init__()
        self._plugin = plugin

    def _normalize_key(self, key):
        """Normalizes the key

        To prevent small errors regarding path joining we define that
        banks use path normalization similar to file systems.

        This means that all paths are relative to '/' and that
        '/path//dir' == '/path/dir'
        """
        res = os.path.normpath(key)
        if not res.startswith("/"):
            res = "/" + res

        if key.endswith("/"):
            res += "/"

        return res

    @classmethod
    def _validate_key(cls, key):
        if not isinstance(key, six.string_types):
            raise exception.InvalidParameterValue(
                err=_('Key must be a string')
            )

        if not cls._KEY_VALIDATION.match(key):
            raise exception.InvalidParameterValue(
                err=_('Only alphanumeric, underscore, dash, dots, at signs, '
                      'and slashes are allowed. Key: "%s"') % key
            )

        if cls._KEY_DOT_VALIDATION.match(key):
            raise exception.InvalidParameterValue(
                err=_('Invalid parameter: must not contain "." or ".." parts')
            )

    def update_object(self, key, value):
        self._validate_key(key)
        return self._plugin.update_object(self._normalize_key(key), value)

    def get_object(self, key):
        self._validate_key(key)
        return self._plugin.get_object(self._normalize_key(key))

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        if not prefix:
            prefix = "/"

        norm_prefix = self._normalize_key(prefix)

        return self._plugin.list_objects(
            prefix=norm_prefix,
            limit=limit,
            marker=marker,
            sort_dir=sort_dir
        )

    def delete_object(self, key):
        self._validate_key(key)
        return self._plugin.delete_object(self._normalize_key(key))

    def get_sub_section(self, section, is_writable=True):
        return BankSection(self, section, is_writable)

    @property
    def is_writeable(self):
        return True

    def get_owner_id(self):
        return self._plugin.get_owner_id()


class BankSection(object):
    """Bank Section compartmentalizes a section of a bank.

    Bank section is used when an object wants to pass a section of
    a bank to another entity and make sure it is only capable of
    accessing part of it.
    """
    _SECTION_VALIDATION = re.compile('^/?[A-Za-z0-9/_.\-@]*/?$')
    _SECTION_DOT_VALIDATION = re.compile('/\.{1,2}(/|$)')

    def __init__(self, bank, section, is_writable=True):
        super(BankSection, self).__init__()
        self._validate_section(section)

        self._bank = bank
        self._prefix = os.path.normpath(section)
        if not self._prefix.startswith('/'):
            self._prefix = '/' + self._prefix
        if not self._prefix.endswith('/'):
            self._prefix += '/'
        self._is_writable = is_writable

    def get_sub_section(self, prefix, is_writable=True):
        if is_writable and not self._is_writable:
            raise exception.BankReadonlyViolation()

        return BankSection(self._bank, self._prefix + '/' + prefix,
                           self._is_writable)

    @classmethod
    def _validate_section(cls, section):
        if not section:
            raise exception.InvalidParameterValue(
                err=_('Empty section')
            )

        if not cls._SECTION_VALIDATION.match(section):
            raise exception.InvalidParameterValue(
                err=_('Invalid section. Must begin and end with a slash, '
                      'and contain valid characters')
            )

        if cls._SECTION_DOT_VALIDATION.match(section):
            raise exception.InvalidParameterValue(
                err=_('Invalid parameter: must not contain "." or ".." parts')
            )

    @property
    def is_writable(self):
        return self._is_writable

    def _prepend_prefix(self, key):
        if not isinstance(key, six.string_types):
            raise exception.InvalidParameterValue(
                err=_('Key must be a string')
            )
        full_key = self._prefix + key
        res = os.path.normpath(full_key)
        if full_key.endswith('/'):
            res += '/'
        return res

    def _validate_writable(self):
        if not self.is_writable:
            raise exception.BankReadonlyViolation()

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

        return [
            key[len(self._prefix):]
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

    def get_owner_id(self):
        return self._bank.get_owner_id()

    @property
    def bank(self):
        return self._bank
