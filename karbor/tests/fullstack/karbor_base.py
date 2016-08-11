# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from cinderclient.v2 import client as cinder_client
from karborclient.v1 import client as karbor_client
from novaclient import client as nova_client

import os_client_config

from oslotest import base


def _get_cloud_config(cloud='devstack-admin'):
    return os_client_config.OpenStackConfig().get_one_cloud(cloud=cloud)


def _credentials(cloud='devstack-admin'):
    """Retrieves credentials to run functional tests

    Credentials are either read via os-client-config from the environment
    or from a config file ('clouds.yaml'). Environment variables override
    those from the config file.

    devstack produces a clouds.yaml with two named clouds - one named
    'devstack' which has user privs and one named 'devstack-admin' which
    has admin privs. This function will default to getting the devstack-admin
    cloud as that is the current expected behavior.
    """
    return _get_cloud_config(cloud=cloud).get_auth_args()


def _get_karbor_client_from_creds():
    api_version = ""
    cloud_config = _get_cloud_config()
    keystone_session = cloud_config.get_session_client("data-protect")
    keystone_auth = cloud_config.get_auth()
    region_name = cloud_config.get_region_name()
    service_type = "data-protect"
    endpoint_type = "publicURL"
    endpoint = keystone_auth.get_endpoint(
        keystone_session,
        service_type=service_type,
        region_name=region_name)

    kwargs = {
        'session': keystone_session,
        'auth': keystone_auth,
        'service_type': service_type,
        'endpoint_type': endpoint_type,
        'region_name': region_name,
    }

    client = karbor_client.Client(api_version, endpoint, **kwargs)
    return client


def _get_cinder_client_from_creds():
    api_version = ""
    cloud_config = _get_cloud_config()
    keystone_session = cloud_config.get_session_client("volumev2")
    keystone_auth = cloud_config.get_auth()
    region_name = cloud_config.get_region_name()
    service_type = "volumev2"
    endpoint_type = "publicURL"
    endpoint = keystone_auth.get_endpoint(
        keystone_session,
        service_type=service_type,
        region_name=region_name)

    kwargs = {
        'session': keystone_session,
        'auth': keystone_auth,
        'service_type': service_type,
        'endpoint_type': endpoint_type,
        'region_name': region_name,
    }

    client = cinder_client.Client(api_version, endpoint, **kwargs)
    return client


def _get_nova_client_from_creds():
    api_version = "2.26"
    cloud_config = _get_cloud_config()
    keystone_session = cloud_config.get_session_client("compute")
    keystone_auth = cloud_config.get_auth()
    region_name = cloud_config.get_region_name()
    service_type = "compute"
    endpoint_type = "publicURL"
    endpoint = keystone_auth.get_endpoint(
        keystone_session,
        service_type=service_type,
        region_name=region_name)

    kwargs = {
        'session': keystone_session,
        'auth': keystone_auth,
        'service_type': service_type,
        'endpoint_type': endpoint_type,
        'region_name': region_name,
    }

    client = nova_client.Client(api_version, endpoint, **kwargs)
    return client


def _get_keystone_endpoint_from_creds():
    cloud_config = _get_cloud_config()
    keystone_session = cloud_config.get_session_client("identity")
    keystone_auth = cloud_config.get_auth()
    region_name = cloud_config.get_region_name()
    service_type = "identity"
    endpoint = keystone_auth.get_endpoint(
        keystone_session,
        service_type=service_type,
        region_name=region_name)
    return endpoint


class ObjectStore(object):
    """Stores objects for later closing.

    ObjectStore can be used to aggregate objects and close them.

    Example:

        with closing(ObjectStore()) as obj_store:
            obj = obj_store.store(SomeObject())

    or:

        obj_store = ObjectStore()
        obj_store.store(SomeObject())
        obj_store.close()
    """

    def __init__(self):
        self._close_funcs = []

    def store(self, obj, close_func=None):
        self._close_funcs.append(close_func if close_func else obj.close)
        return obj

    def close(self):
        for close_func in reversed(self._close_funcs):
            close_func()


class KarborBaseTest(base.BaseTestCase):
    """Basic class for karbor fullstack testing.

    This class has common code shared for karbor fullstack testing
    including the various clients (karbor) and common
    setup/cleanup code.
    """

    def setUp(self):
        super(KarborBaseTest, self).setUp()
        self.cinder_client = _get_cinder_client_from_creds()
        self.nova_client = _get_nova_client_from_creds()
        self.karbor_client = _get_karbor_client_from_creds()
        self.keystone_endpoint = _get_keystone_endpoint_from_creds()
        self._testcase_store = ObjectStore()

    def store(self, obj, close_func=None):
        return self._testcase_store.store(obj, close_func)

    def tearDown(self):
        self._testcase_store.close()
        super(KarborBaseTest, self).tearDown()

    def provider_list(self):
        return self.karbor_client.providers.list()
