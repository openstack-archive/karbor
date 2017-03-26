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

import math
import time

from karbor import exception
from karbor.i18n import _
from karbor.services.protection.bank_plugin import BankPlugin
from karbor.services.protection.bank_plugin import LeasePlugin
from karbor.services.protection import client_factory
from oslo_config import cfg
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_service import loopingcall
from oslo_utils import uuidutils
from swiftclient import ClientException


swift_bank_plugin_opts = [
    cfg.StrOpt('bank_swift_object_container',
               default='karbor',
               help='The default swift container to use.'),
]

LOG = logging.getLogger(__name__)

lease_opt = [cfg.IntOpt('lease_expire_window',
                        default=600,
                        help='expired_window for bank lease, in seconds'),
             cfg.IntOpt('lease_renew_window',
                        default=120,
                        help='period for bank lease, in seconds, '
                             'between bank lease client renew the lease'),
             cfg.IntOpt('lease_validity_window',
                        default=100,
                        help='validity_window for bank lease, in seconds'), ]


class SwiftConnectionFailed(exception.KarborException):
    message = _("Connection to swift failed: %(reason)s")


class SwiftBankPlugin(BankPlugin, LeasePlugin):
    """Swift bank plugin"""
    def __init__(self, config, context=None):
        super(SwiftBankPlugin, self).__init__(config)
        self._config.register_opts(swift_bank_plugin_opts,
                                   "swift_bank_plugin")
        self._config.register_opts(lease_opt,
                                   "swift_bank_plugin")
        plugin_cfg = self._config.swift_bank_plugin
        self.bank_object_container = plugin_cfg.bank_swift_object_container
        self.lease_expire_window = plugin_cfg.lease_expire_window
        self.lease_renew_window = plugin_cfg.lease_renew_window
        self.context = context
        # TODO(luobin):
        # init lease_validity_window
        # according to lease_renew_window if not configured
        self.lease_validity_window = plugin_cfg.lease_validity_window

        # TODO(luobin): create a uuid of this bank_plugin
        self.owner_id = uuidutils.generate_uuid()
        self.lease_expire_time = 0
        self.bank_leases_container = "leases"
        self._connection = None

    def _setup_connection(self):
        return client_factory.ClientFactory.create_client('swift',
                                                          self.context,
                                                          self._config)

    @property
    def connection(self):
        if not self._connection:
            _connection = self._setup_connection()
            # create container
            try:
                _connection.put_container(self.bank_object_container)
                _connection.put_container(self.bank_leases_container)
            except SwiftConnectionFailed as err:
                LOG.error("bank plugin create container failed.")
                raise exception.CreateContainerFailed(reason=err)
            self._connection = _connection

            # acquire lease
            try:
                self.acquire_lease()
            except exception.AcquireLeaseFailed:
                LOG.error("bank plugin acquire lease failed.")
                raise

            # start renew lease
            renew_lease_loop = loopingcall.FixedIntervalLoopingCall(
                self.renew_lease)
            renew_lease_loop.start(interval=self.lease_renew_window,
                                   initial_delay=self.lease_renew_window)
        return self._connection

    def get_owner_id(self):
        return self.owner_id

    def update_object(self, key, value):
        serialized = False
        try:
            if not isinstance(value, str):
                value = jsonutils.dumps(value)
                serialized = True
            self._put_object(container=self.bank_object_container,
                             obj=key,
                             contents=value,
                             headers={
                                 'x-object-meta-serialized': str(serialized)
                             })
        except SwiftConnectionFailed as err:
            LOG.error("update object failed, err: %s.", err)
            raise exception.BankUpdateObjectFailed(reason=err, key=key)

    def delete_object(self, key):
        try:
            self._delete_object(container=self.bank_object_container,
                                obj=key)
        except SwiftConnectionFailed as err:
            LOG.error("delete object failed, err: %s.", err)
            raise exception.BankDeleteObjectFailed(reason=err, key=key)

    def get_object(self, key):
        try:
            return self._get_object(container=self.bank_object_container,
                                    obj=key)
        except SwiftConnectionFailed as err:
            LOG.error("get object failed, err: %s.", err)
            raise exception.BankGetObjectFailed(reason=err, key=key)

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None):
        try:
            if sort_dir == "desc":
                body = self._get_container(
                    container=self.bank_object_container,
                    prefix=prefix, end_marker=marker)
                limit_objects = body[-limit:] if limit is not None else body
                return [obj.get("name") for obj in limit_objects]
            else:
                body = self._get_container(
                    container=self.bank_object_container,
                    prefix=prefix, limit=limit, marker=marker)
                return [obj.get("name") for obj in body]
        except SwiftConnectionFailed as err:
            LOG.error("list objects failed, err: %s.", err)
            raise exception.BankListObjectsFailed(reason=err)

    def acquire_lease(self):
        container = self.bank_leases_container
        obj = self.owner_id
        contents = self.owner_id
        headers = {'X-Delete-After': str(self.lease_expire_window)}
        try:
            self._put_object(container=container,
                             obj=obj,
                             contents=contents,
                             headers=headers)
            self.lease_expire_time = math.floor(
                time.time()) + self.lease_expire_window
        except SwiftConnectionFailed as err:
            LOG.error("acquire lease failed, err:%s.", err)
            raise exception.AcquireLeaseFailed(reason=err)

    def renew_lease(self):
        container = self.bank_leases_container
        obj = self.owner_id
        headers = {'X-Delete-After': str(self.lease_expire_window)}
        try:
            self._post_object(container=container,
                              obj=obj,
                              headers=headers)
            self.lease_expire_time = math.floor(
                time.time()) + self.lease_expire_window
        except SwiftConnectionFailed as err:
            LOG.error("acquire lease failed, err:%s.", err)

    def check_lease_validity(self):
        if (self.lease_expire_time - math.floor(time.time()) >=
                self.lease_validity_window):
            return True
        else:
            return False

    def _put_object(self, container, obj, contents, headers=None):
        try:
            self.connection.put_object(container=container,
                                       obj=obj,
                                       contents=contents,
                                       headers=headers)
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)

    def _get_object(self, container, obj):
        try:
            (_resp, body) = self.connection.get_object(container=container,
                                                       obj=obj)
            if _resp.get("x-object-meta-serialized").lower() == "true":
                body = jsonutils.loads(body)
            return body
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)

    def _post_object(self, container, obj, headers):
        try:
            self.connection.post_object(container=container,
                                        obj=obj,
                                        headers=headers)
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)

    def _delete_object(self, container, obj):
        try:
            self.connection.delete_object(container=container,
                                          obj=obj)
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)

    def _put_container(self, container):
        try:
            self.connection.put_container(container=container)
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)

    def _get_container(self, container, prefix=None, limit=None, marker=None,
                       end_marker=None):
        try:
            (_resp, body) = self.connection.get_container(
                container=container,
                prefix=prefix,
                limit=limit,
                marker=marker,
                end_marker=end_marker)
            return body
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)
