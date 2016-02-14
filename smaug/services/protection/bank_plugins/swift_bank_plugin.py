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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from smaug import exception
from smaug.i18n import _, _LE
from smaug.services.protection.bank_plugin import BankPlugin
from smaug.services.protection.bank_plugin import LeasePlugin
from swiftclient import client as swift
from swiftclient import ClientException
import time
import uuid

swift_client_opts = [
    cfg.StrOpt('bank_swift_url',
               help='The URL of the Swift endpoint'),
    cfg.StrOpt('bank_swift_auth_url',
               help='The URL of the Keystone endpoint'),
    cfg.StrOpt('bank_swift_auth',
               default='single_user',
               help='Swift authentication mechanism'),
    cfg.StrOpt('bank_swift_auth_version',
               default='1',
               help='Swift authentication version. '
                    'Specify "1" for auth 1.0, or "2" for auth 2.0'),
    cfg.StrOpt('bank_swift_tenant_name',
               help='Swift tenant/account name. '
                    'Required when connecting to an auth 2.0 system'),
    cfg.StrOpt('bank_swift_user',
               help='Swift user name'),
    cfg.StrOpt('bank_swift_key',
               help='Swift key for authentication'),
    cfg.IntOpt('bank_swift_retry_attempts',
               default=3,
               help='The number of retries to make for '
                    'Swift operations'),
    cfg.IntOpt('bank_swift_retry_backoff',
               default=2,
               help='The backoff time in seconds '
                    'between Swift retries'),
    cfg.StrOpt('bank_swift_ca_cert_file',
               help='Location of the CA certificate file '
                    'to use for swift client requests.'),
    cfg.BoolOpt('bank_swift_auth_insecure',
                default=False,
                help='Bypass verification of server certificate when '
                     'making SSL connection to Swift.'),
]

CONF = cfg.CONF
CONF.register_opts(swift_client_opts, "swift_client")
LOG = logging.getLogger(__name__)


class SwiftConnectionFailed(exception.SmaugException):
    message = _("Connection to swift failed: %(reason)s")


class SwiftBankPlugin(BankPlugin, LeasePlugin):
    def __init__(self, context, object_container):
        super(BankPlugin, self).__init__()
        self.context = context
        self.swift_retry_attempts = CONF.swift_client.bank_swift_retry_attempts
        self.swift_retry_backoff = CONF.swift_client.bank_swift_retry_backoff
        self.swift_auth_insecure = CONF.swift_client.bank_swift_auth_insecure
        self.swift_ca_cert_file = CONF.swift_client.bank_swift_ca_cert_file
        self.lease_expire_window = CONF.lease_expire_window
        self.lease_renew_window = CONF.lease_renew_window
        # TODO(luobin):
        # init lease_validity_window
        # according to lease_renew_window if not configured
        self.lease_validity_window = CONF.lease_validity_window

        # TODO(luobin): create a uuid of this bank_plugin
        self.owner_id = str(uuid.uuid4())
        self.lease_expire_time = 0
        self.bank_leases_container = "leases"
        self.bank_object_container = object_container
        self.connection = self._setup_connection()

        # create container
        try:
            self._put_container(self.bank_object_container)
            self._put_container(self.bank_leases_container)
        except SwiftConnectionFailed as err:
            LOG.error(_LE("bank plugin create container failed."))
            raise exception.CreateContainerFailed(reason=err)

        # acquire lease
        try:
            self.acquire_lease()
        except exception.AcquireLeaseFailed as err:
            LOG.error(_LE("bank plugin acquire lease failed."))
            raise err

        # start renew lease
        renew_lease_loop = loopingcall.FixedIntervalLoopingCall(
            self.renew_lease)
        renew_lease_loop.start(interval=self.lease_renew_window,
                               initial_delay=self.lease_renew_window)

    def _setup_connection(self):
        if CONF.swift_client.bank_swift_auth == "single_user":
            connection = swift.Connection(
                authurl=CONF.swift_client.bank_swift_auth_url,
                auth_version=CONF.swift_client.bank_swift_auth_version,
                tenant_name=CONF.swift_client.bank_swift_tenant_name,
                user=CONF.swift_client.bank_swift_user,
                key=CONF.swift_client.bank_swift_key,
                retries=self.swift_retry_attempts,
                starting_backoff=self.swift_retry_backoff,
                insecure=self.swift_auth_insecure,
                cacert=self.swift_ca_cert_file)
        else:
            connection = swift.Connection(
                preauthurl=CONF.swift_client.bank_swift_url,
                preauthtoken=self.context.auth_token,
                retries=self.swift_retry_attempts,
                starting_backoff=self.swift_retry_backoff,
                insecure=self.swift_auth_insecure,
                cacert=self.swift_ca_cert_file)
        return connection

    def create_object(self, key, value):
        try:
            self._put_object(container=self.bank_object_container,
                             obj=key,
                             contents=value)
        except SwiftConnectionFailed as err:
            LOG.error(_LE("create object failed, err: %s."), err)
            raise exception.BankCreateObjectFailed(reasone=err,
                                                   key=key)

    def update_object(self, key, value):
        try:
            self._put_object(container=self.bank_object_container,
                             obj=key,
                             contents=value)
        except SwiftConnectionFailed as err:
            LOG.error(_LE("update object failed, err: %s."), err)
            raise exception.BankUpdateObjectFailed(reasone=err,
                                                   key=key)

    def delete_object(self, key):
        try:
            self._delete_object(container=self.bank_object_container,
                                obj=key)
        except SwiftConnectionFailed as err:
            LOG.error(_LE("delete object failed, err: %s."), err)
            raise exception.BankDeleteObjectFailed(reasone=err,
                                                   key=key)

    def get_object(self, key):
        try:
            return self._get_object(container=self.bank_object_container,
                                    obj=key)
        except SwiftConnectionFailed as err:
            LOG.error(_LE("get object failed, err: %s."), err)
            raise exception.BankGetObjectFailed(reasone=err,
                                                key=key)

    def list_objects(self, prefix=None, limit=None, marker=None):
        object_names = []
        try:
            body = self._get_container(container=self.bank_object_container,
                                       prefix=prefix,
                                       limit=limit,
                                       marker=marker)
        except SwiftConnectionFailed as err:
            LOG.error(_LE("list objects failed, err: %s."), err)
            raise exception.BankListObjectsFailed(reasone=err)
        for obj in body:
            if obj.get("name"):
                object_names.append(obj.get("name"))
        return object_names

    def acquire_lease(self):
        container = self.bank_leases_container
        obj = self.owner_id
        contents = self.owner_id
        headers = {'X-Delete-After': self.lease_expire_window}
        try:
            self._put_object(container=container,
                             obj=obj,
                             contents=contents,
                             headers=headers)
            self.lease_expire_time = long(
                time.time()) + self.lease_expire_window
        except SwiftConnectionFailed as err:
            LOG.error(_LE("acquire lease failed, err:%s."), err)
            raise exception.AcquireLeaseFailed(reason=err)

    def renew_lease(self):
        container = self.bank_leases_container
        obj = self.owner_id
        headers = {'X-Delete-After': self.lease_expire_window}
        try:
            self._post_object(container=container,
                              obj=obj,
                              headers=headers)
            self.lease_expire_time = long(
                time.time()) + self.lease_expire_window
        except SwiftConnectionFailed as err:
            LOG.error(_LE("acquire lease failed, err:%s."), err)

    def check_lease_validity(self):
        if (self.lease_expire_time - long(time.time()) >=
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

    def _get_container(self, container, prefix=None, limit=None, marker=None):
        try:
            (_resp, body) = self.connection.get_container(
                container=container,
                prefix=prefix,
                limit=limit,
                marker=marker)
            return body
        except ClientException as err:
            raise SwiftConnectionFailed(reason=err)
