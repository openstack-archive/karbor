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

from kubernetes import client
from kubernetes.client import api_client
from kubernetes.client.configuration import Configuration

from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)
SERVICE = 'k8s'
kubernetes_client_opts = [
    cfg.StrOpt(SERVICE + '_host',
               help='The IP address of the kubernetes api server.'),
    cfg.StrOpt(SERVICE + '_ssl_ca_cert',
               help='The certificate authority will be used for secure '
                    'access from Admission Controllers.'),
    cfg.StrOpt(SERVICE + '_cert_file',
               help='The client certificate file for the kubernetes '
                    'cluster.'),
    cfg.StrOpt(SERVICE + '_key_file',
               help='The client key file for the kubernetes cluster.')
]


def register_opts(conf):
    conf.register_opts(kubernetes_client_opts, group=SERVICE + '_client')


def create(context, conf, **kwargs):
    register_opts(conf)

    client_config = conf.k8s_client
    LOG.info('Creating the kubernetes client with url %s.',
             client_config.k8s_host)

    config = Configuration()
    config.host = client_config.k8s_host
    config.ssl_ca_cert = client_config.k8s_ssl_ca_cert
    config.cert_file = client_config.k8s_cert_file
    config.key_file = client_config.k8s_key_file
    k8s_api_client = api_client.ApiClient(config)
    k8s_core_v1_api = client.CoreV1Api(k8s_api_client)
    return k8s_core_v1_api
