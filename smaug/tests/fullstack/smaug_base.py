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
from novaclient.v2 import client as nova_client
from smaugclient.v1 import client as smaug_client

import os_client_config

from oslotest import base
from time import sleep


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


def _get_smaug_client_from_creds():
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

    client = smaug_client.Client(api_version, endpoint, **kwargs)
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
    api_version = ""
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


class SmaugBaseTest(base.BaseTestCase):
    """Basic class for Smaug fullstack testing

    This class has common code shared for Smaug fullstack testing
    including the various clients (smaug) and common
    setup/cleanup code.
    """
    def setUp(self):
        super(SmaugBaseTest, self).setUp()
        self.cinder_client = _get_cinder_client_from_creds()
        self.nova_client = _get_nova_client_from_creds()
        self.smaug_client = _get_smaug_client_from_creds()

    def tearDown(self):
        self.cleanup_plans()
        self.cleanup_volumes()
        self.cleanup_backup_volumes()
        super(SmaugBaseTest, self).tearDown()

    def provider_list(self):
        return self.smaug_client.providers.list()

    def create_volume(self, size, name=None):
        volume = self.cinder_client.volumes.create(size, name=name)
        sleep(10)
        return volume

    def delete_volume(self, volume_id):
        self.cinder_client.volumes.delete(volume_id)
        sleep(30)

    def cleanup_plans(self):
        plans = self.smaug_client.plans.list()
        for plan in plans:
            self.smaug_client.plans.delete(plan.get("id"))

    def cleanup_volumes(self):
        volumes = self.cinder_client.volumes.list()
        for volume in volumes:
            self.cinder_client.volumes.delete(volume.id)
            sleep(18)

    def cleanup_backup_volumes(self):
        backups = self.cinder_client.backups.list()
        for backup in backups:
            self.cinder_client.backups.delete(backup.id)
            sleep(18)
