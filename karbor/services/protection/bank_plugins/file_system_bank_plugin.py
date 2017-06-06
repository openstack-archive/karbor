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
import errno
import os

from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import uuidutils

from karbor import exception
from karbor.i18n import _
from karbor.services.protection.bank_plugin import BankPlugin

import six

file_system_bank_plugin_opts = [
    cfg.StrOpt('file_system_bank_path',
               help='The file system bank path to use.'),
    cfg.StrOpt('bank_object_container',
               default='karbor',
               help='The file system bank container to use.'),
]

LOG = logging.getLogger(__name__)


class FileSystemBankPlugin(BankPlugin):
    """File system bank plugin"""
    def __init__(self, config):
        super(FileSystemBankPlugin, self).__init__(config)
        self._config.register_opts(file_system_bank_plugin_opts,
                                   "file_system_bank_plugin")
        plugin_cfg = self._config.file_system_bank_plugin
        self.file_system_bank_path = plugin_cfg.file_system_bank_path
        self.bank_object_container = plugin_cfg.bank_object_container

        try:
            self._create_dir(self.file_system_bank_path)
            self.object_container_path = "/".join([self.file_system_bank_path,
                                                   self.bank_object_container])
            self._create_dir(self.object_container_path)
        except OSError as err:
            LOG.exception(_("Init file system bank failed. err: %s"), err)

        self.owner_id = uuidutils.generate_uuid()

    def _validate_path(self, path):
        if path.find('..') >= 0:
            msg = (_("The path(%s) is invalid.") % path)
            raise exception.InvalidInput(msg)

    def _create_dir(self, path):
        try:
            original_umask = None
            try:
                original_umask = os.umask(0)
                os.makedirs(path)
            finally:
                os.umask(original_umask)
        except OSError as err:
            if err.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                LOG.exception(_("Create the directory failed. path: %s"), path)
                raise

    def _write_object(self, path, data):
        obj_file_name = None
        try:
            obj_path = self.object_container_path + path.rsplit('/', 1)[0]
            obj_file_name = self.object_container_path + path
            self._create_dir(obj_path)
            mode = "wb"
            if isinstance(data, six.string_types):
                mode = "w"
            with open(obj_file_name, mode=mode) as obj_file:
                obj_file.write(data)
        except (OSError, IOError):
            LOG.exception(_("Write object failed. name: %s"), obj_file_name)
            raise

    def _get_object(self, path):
        obj_file_name = self.object_container_path + path
        if not os.path.isfile(obj_file_name):
            LOG.exception(_("Object is not a file. name: %s"), obj_file_name)
            raise
        try:
            with open(obj_file_name, mode='r') as obj_file:
                data = obj_file.read()
                return data
        except OSError:
            LOG.exception(_("Get object failed. name: %s"), obj_file_name)
            raise

    def _delete_object(self, path):
        obj_path = self.object_container_path + path.rsplit('/', 1)[0]
        obj_file_name = self.object_container_path + path
        try:
            os.remove(obj_file_name)
            if not os.listdir(obj_path) and (
                    obj_path != self.object_container_path):
                os.rmdir(obj_path)
        except OSError:
            LOG.exception(_("Delete the object failed. name: %s"),
                          obj_file_name)
            raise

    def _list_object(self, path):
        obj_file_path = self.object_container_path + path
        if not os.path.isdir(obj_file_path):
            LOG.exception(_("Path is not a directory. name: %s"),
                          obj_file_path)
            raise
        try:
            if os.path.isdir(obj_file_path):
                return os.listdir(obj_file_path)
            else:
                base_dir = os.path.dirname(obj_file_path)
                base_name = os.path.basename(obj_file_path)
                return (
                    base_dir + '/' + obj_file
                    for obj_file in os.listdir(base_dir)
                    if obj_file.startswith(base_name)
                )
        except OSError:
            LOG.exception(_("List the object failed. path: %s"), obj_file_path)
            raise

    def get_owner_id(self):
        return self.owner_id

    def update_object(self, key, value):
        LOG.debug("FsBank: update_object. key: %s", key)
        self._validate_path(key)
        try:
            if not isinstance(value, str):
                value = jsonutils.dumps(value)
            self._write_object(path=key,
                               data=value)
        except OSError as err:
            LOG.error("Update object failed. err: %s", err)
            raise exception.BankUpdateObjectFailed(reason=err,
                                                   key=key)

    def delete_object(self, key):
        LOG.debug("FsBank: delete_object. key: %s", key)
        self._validate_path(key)
        try:
            self._delete_object(path=key)
        except OSError as err:
            LOG.error("Delete object failed. err: %s", err)
            raise exception.BankDeleteObjectFailed(reason=err,
                                                   key=key)

    def get_object(self, key):
        LOG.debug("FsBank: get_object. key: %s", key)
        self._validate_path(key)
        try:
            data = self._get_object(path=key)
        except OSError as err:
            LOG.error("Get object failed. err: %s", err)
            raise exception.BankGetObjectFailed(reason=err,
                                                key=key)
        if isinstance(data, six.string_types):
            try:
                data = jsonutils.loads(data)
            except ValueError:
                pass
        return data

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        LOG.debug("FsBank: list_objects. key: %s", prefix)
        try:
            file_lists = self._list_object(prefix)
            return (
                file_lists[-limit:] if limit is not None else file_lists)
        except OSError as err:
            LOG.error("List objects failed. err: %s", err)
            raise exception.BankListObjectsFailed(reason=err)
