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
import botocore
import botocore.session
import logging
from oslo_config import cfg

LOG = logging.getLogger(__name__)
SERVICE = 's3'
s3_client_opts = [
    cfg.StrOpt(SERVICE + '_endpoint',
               help='URL of the S3 compatible storage endpoint.'),
    cfg.StrOpt(SERVICE + '_access_key',
               help='Access key for S3 compatible storage.'),
    cfg.StrOpt(SERVICE + '_secret_key',
               secret=True,
               help='Secret key for S3 compatible storage.'),
    cfg.IntOpt(SERVICE + '_retry_attempts',
               default=3,
               help='The number of retries to make for '
                    'S3 operations'),
    cfg.IntOpt(SERVICE + '_retry_backoff',
               default=2,
               help='The backoff time in seconds '
                    'between S3 retries')
]


def register_opts(conf):
    conf.register_opts(s3_client_opts, group=SERVICE + '_client')


def create(context, conf, **kwargs):
    register_opts(conf)

    client_config = conf.s3_client
    LOG.info('Creating s3 client with url %s.',
             client_config.s3_endpoint)
    return botocore.session.get_session().create_client(
        's3',
        aws_access_key_id=client_config.s3_access_key,
        aws_secret_access_key=client_config.s3_secret_key,
        endpoint_url=client_config.s3_endpoint
    )
