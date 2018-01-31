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

import logging as log
import math
import time

from botocore.exceptions import ClientError
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

s3_bank_plugin_opts = [
    cfg.StrOpt('bank_s3_object_bucket',
               default='karbor',
               help='The default s3 object bucket to use.'),
    cfg.StrOpt('bank_s3_lease_bucket',
               default='lease',
               help='The default s3 lease bucket to use.'),
]

LOG = logging.getLogger(__name__)
log.getLogger('botocore').setLevel(log.WARNING)

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


class S3ConnectionFailed(exception.KarborException):
    message = _("Connection to s3 failed: %(reason)s")


class S3BankPlugin(BankPlugin, LeasePlugin):
    """S3 bank plugin"""
    def __init__(self, config, context=None):
        super(S3BankPlugin, self).__init__(config)
        self._config.register_opts(s3_bank_plugin_opts,
                                   "s3_bank_plugin")
        self._config.register_opts(lease_opt,
                                   "s3_bank_plugin")
        plugin_cfg = self._config.s3_bank_plugin
        self.bank_object_bucket = plugin_cfg.bank_s3_object_bucket
        self.lease_expire_window = plugin_cfg.lease_expire_window
        self.lease_renew_window = plugin_cfg.lease_renew_window
        self.context = context
        self.lease_validity_window = plugin_cfg.lease_validity_window

        self.owner_id = uuidutils.generate_uuid()
        self.lease_expire_time = 0
        self.bank_leases_bucket = plugin_cfg.bank_s3_lease_bucket
        self._connection = None

    def _setup_connection(self):
        return client_factory.ClientFactory.create_client(
            's3',
            self.context,
            self._config
        )

    @property
    def connection(self):
        if not self._connection:
            _connection = self._setup_connection()
            # create bucket
            try:
                _connection.create_bucket(Bucket=self.bank_object_bucket)
                _connection.create_bucket(Bucket=self.bank_leases_bucket)
            except S3ConnectionFailed as err:
                LOG.error("bank plugin create bucket failed.")
                raise exception.CreateBucketrFailed(reason=err)
            self._connection = _connection

            # acquire lease
            try:
                self.acquire_lease()
            except exception.AcquireLeaseFailed:
                LOG.error("bank plugin acquire lease failed.")
                raise

            # start renew lease
            renew_lease_loop = loopingcall.FixedIntervalLoopingCall(
                self.renew_lease
            )
            renew_lease_loop.start(
                interval=self.lease_renew_window,
                initial_delay=self.lease_renew_window
            )
        return self._connection

    def get_owner_id(self, context=None):
        return self.owner_id

    def update_object(self, key, value, context=None):
        serialized = False
        try:
            if not isinstance(value, str):
                value = jsonutils.dumps(value)
                serialized = True
            self._put_object(bucket=self.bank_object_bucket,
                             obj=key,
                             contents=value,
                             headers={
                                 'x-object-meta-serialized': str(serialized)
                             })
        except S3ConnectionFailed as err:
            LOG.error("update object failed, err: %s.", err)
            raise exception.BankUpdateObjectFailed(reason=err, key=key)

    def delete_object(self, key, context=None):
        try:
            self._delete_object(bucket=self.bank_object_bucket,
                                obj=key)
        except S3ConnectionFailed as err:
            LOG.error("delete object failed, err: %s.", err)
            raise exception.BankDeleteObjectFailed(reason=err, key=key)

    def get_object(self, key, context=None):
        try:
            return self._get_object(bucket=self.bank_object_bucket,
                                    obj=key)
        except S3ConnectionFailed as err:
            LOG.error("get object failed, err: %s.", err)
            raise exception.BankGetObjectFailed(reason=err, key=key)

    def list_objects(self, prefix=None, limit=None, marker=None,
                     sort_dir=None, context=None):
        try:
            response = self._get_bucket(
                bucket=self.bank_object_bucket,
                prefix=prefix,
                limit=limit,
                marker=marker
            )
            return [obj['Key'] for obj in response]
        except S3ConnectionFailed as err:
            LOG.error("list objects failed, err: %s.", err)
            raise exception.BankListObjectsFailed(reason=err)

    def acquire_lease(self):
        bucket = self.bank_leases_bucket
        obj = self.owner_id
        contents = self.owner_id
        self.lease_expire_time = \
            math.floor(time.time()) + self.lease_expire_window
        headers = {'lease-expire-time': str(self.lease_expire_time)}
        try:
            self._put_object(bucket=bucket,
                             obj=obj,
                             contents=contents,
                             headers=headers)
        except S3ConnectionFailed as err:
            LOG.error("acquire lease failed, err:%s.", err)
            raise exception.AcquireLeaseFailed(reason=err)

    def renew_lease(self):
        self.acquire_lease()

    def check_lease_validity(self):
        if (self.lease_expire_time - math.floor(time.time()) >=
                self.lease_validity_window):
            return True
        else:
            self._delete_object(
                bucket=self.bank_leases_bucket,
                obj=self.owner_id
            )
            return False

    def _put_object(self, bucket, obj, contents, headers=None):
        try:
            self.connection.put_object(
                Bucket=bucket,
                Key=obj,
                Body=contents,
                Metadata=headers
            )
        except ClientError as err:
            raise S3ConnectionFailed(reason=err)

    def _get_object(self, bucket, obj):
        try:
            response = self.connection.get_object(Bucket=bucket, Key=obj)
            body = response['Body'].read()
            if response['Metadata']["x-object-meta-serialized"]\
                    .lower() == "true":
                body = jsonutils.loads(body)
            return body
        except ClientError as err:
            raise S3ConnectionFailed(reason=err)

    def _delete_object(self, bucket, obj):
        try:
            self.connection.delete_object(Bucket=bucket,
                                          Key=obj)
        except ClientError as err:
            raise S3ConnectionFailed(reason=err)

    def _get_bucket(self, bucket, prefix=None, limit=None,
                    marker=None):
        try:
            prefix = '' if prefix is None else prefix
            marker = '' if marker is None else marker
            objects_to_return = []
            if limit is None:
                is_truncated = True
                while is_truncated:
                    response = self.connection.list_objects(
                        Bucket=bucket,
                        Prefix=prefix,
                        Marker=marker
                    )
                    if 'Contents' not in response:
                        break

                    is_truncated = response['IsTruncated']
                    objects_to_return.extend(response['Contents'])
                    marker = response['Contents'][-1]['Key']
            else:
                response = self.connection.list_objects(
                    Bucket=bucket,
                    Prefix=prefix,
                    MaxKeys=limit,
                    Marker=marker
                )

                if 'Contents' in response:
                    objects_to_return.extend(response['Contents'])

        except ClientError as err:
            raise S3ConnectionFailed(reason=err)
        else:
            return objects_to_return
