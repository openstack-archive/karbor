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

from cinderclient import client as cinder_client
from glanceclient import client as glance_client
from karborclient import client as karbor_client
from manilaclient import client as manilaclient
from neutronclient.v2_0 import client as neutron_client
from novaclient import client as nova_client

import os_client_config

from oslotest import base


def _get_cloud_config(cloud='devstack'):
    return os_client_config.OpenStackConfig().get_one_cloud(cloud=cloud)


def _credentials(cloud='devstack'):
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


def _get_endpoint(service_type):
    cloud_config = _get_cloud_config()
    keystone_session = cloud_config.get_session_client(service_type)
    keystone_auth = cloud_config.get_auth()
    region_name = cloud_config.get_region_name()
    return keystone_auth.get_endpoint(
        keystone_session,
        service_type=service_type,
        region_name=region_name,
    )


def _get_client_args(service_type, endpoint_type="publicURL"):
    cloud_config = _get_cloud_config()
    keystone_session = cloud_config.get_session_client(service_type)
    keystone_auth = cloud_config.get_auth()
    region_name = cloud_config.get_region_name()
    return {
        'session': keystone_session,
        'auth': keystone_auth,
        'service_type': service_type,
        'endpoint_type': endpoint_type,
        'region_name': region_name,
    }


def _get_karbor_client(api_version='1'):
    kwargs = _get_client_args('data-protect')
    client = karbor_client.Client(api_version, **kwargs)
    return client


def _get_cinder_client(api_version='3'):
    kwargs = _get_client_args('volumev3')
    client = cinder_client.Client(api_version, **kwargs)
    return client


def _get_manila_client(api_version='2'):
    kwargs = _get_client_args('sharev2')
    client = manilaclient.Client(api_version, **kwargs)
    return client


def _get_glance_client(api_version='2'):
    kwargs = _get_client_args('image')
    kwargs.pop('endpoint_type')
    client = glance_client.Client(api_version, **kwargs)
    return client


def _get_nova_client(api_version='2.26'):
    kwargs = _get_client_args('compute')
    client = nova_client.Client(api_version, **kwargs)
    return client


def _get_neutron_client(api_version='2'):
    kwargs = _get_client_args('network')
    client = neutron_client.Client(**kwargs)
    return client


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
        super(ObjectStore, self).__init__()
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
        self.cinder_client = _get_cinder_client()
        self.manila_client = _get_manila_client()
        self.glance_client = _get_glance_client()
        self.nova_client = _get_nova_client()
        self.neutron_client = _get_neutron_client()
        self.karbor_client = _get_karbor_client()
        self.keystone_endpoint = _get_endpoint('identity')
        self._testcase_store = ObjectStore()
        self.provider_id_noop = 'b766f37c-d011-4026-8228-28730d734a3f'
        self.provider_id_os = 'cf56bd3e-97a7-4078-b6d5-f36246333fd9'
        self.provider_id_fs_bank = '6659007d-6f66-4a0f-9cb4-17d6aded0bb9'
        self.provider_id_os_volume_snapshot = (
            '90d5bfea-a259-41e6-80c6-dcfcfcd9d827')

    def store(self, obj, close_func=None):
        return self._testcase_store.store(obj, close_func)

    def tearDown(self):
        self._testcase_store.close()
        super(KarborBaseTest, self).tearDown()

    def provider_list(self):
        return self.karbor_client.providers.list()
