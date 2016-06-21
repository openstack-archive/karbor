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
from functools import partial

from smaug.common import constants
from smaug.tests.fullstack import smaug_base as base
from smaug.tests.fullstack import utils

SHORT_TIMEOUT = 30
MEDIUM_TIMEOUT = 90
LONG_TIMEOUT = 360

SHORT_SLEEP = 2
MEDIUM_SLEEP = 5
LONG_SLEEP = 10

DEFAULT_IMAGE = "cirros-0.3.4-x86_64-uec"
DEFAULT_FLAVOR = "cirros256"


class Checkpoint(object):
    def __init__(self):
        self.id = None
        self._provider_id = None
        self.smaug_client = base._get_smaug_client_from_creds()

    def _checkpoint_status(self, status=None):
        try:
            cp = self.smaug_client.checkpoints.get(self._provider_id, self.id)
        except Exception:
            return False

        if status is None or cp.status == status:
            return True
        else:
            return False

    def create(self, provider_id, plan_id, timeout=LONG_TIMEOUT):
        self._provider_id = provider_id
        checkpoint = self.smaug_client.checkpoints.create(provider_id,
                                                          plan_id)
        self.id = checkpoint.id
        utils.wait_until_true(partial(self._checkpoint_status,
                                      constants.CHECKPOINT_STATUS_AVAILABLE),
                              timeout=timeout, sleep=LONG_SLEEP)
        return self.id

    def close(self, timeout=LONG_TIMEOUT):
        try:
            self.smaug_client.checkpoints.delete(self._provider_id, self.id)
        except Exception:
            return
        utils.wait_until_true(partial(self._checkpoint_status,
                                      constants.CHECKPOINT_STATUS_DELETED),
                              timeout=timeout, sleep=LONG_SLEEP)


class Plan(object):
    _name_id = 0

    def __init__(self):
        self.id = None
        self.smaug_client = base._get_smaug_client_from_creds()

    def create(self, provider_id, resources,
               parameters={"dummy": {"dummy": "dummy"}}, name=None):
        def _transform_resource(resource):
            if isinstance(resource, dict):
                return resource
            if hasattr(resource, 'to_dict') and callable(resource.to_dict):
                return resource.to_dict()

        if name is None:
            name = "SmaugFullstack-Plan-{id}".format(id=self._name_id)
            self._name_id += 1

        resources = map(_transform_resource, resources)
        plan = self.smaug_client.plans.create(name, provider_id, resources,
                                              parameters)
        self.id = plan.id
        return self.id

    def update(self, data):
        return self.smaug_client.plans.update(self.id, data)

    def close(self):
        try:
            self.smaug_client.plans.delete(self.id)
        except Exception:
            return


class Restore(object):
    def __init__(self):
        self.id = None
        self.smaug_client = base._get_smaug_client_from_creds()

    def _restore_status(self, status=None):
        try:
            restore = self.smaug_client.restores.get(self.id)
        except Exception:
            return False

        if status is None or restore.status == status:
            return True
        else:
            return False

    def create(self, provider_id, checkpoint_id, target, parameters,
               timeout=LONG_TIMEOUT):
        restore = self.smaug_client.restores.create(provider_id,
                                                    checkpoint_id,
                                                    target,
                                                    parameters)
        self.id = restore.id
        utils.wait_until_true(partial(self._restore_status, 'success'),
                              timeout=timeout, sleep=LONG_SLEEP)
        return self.id

    def close(self):
        pass


class Trigger(object):
    _name_id = 0

    def __init__(self):
        self.id = None
        self.smaug_client = base._get_smaug_client_from_creds()

    def create(self, type, properties, name=None):
        if name is None:
            name = "SmaugFullstack-Trigger-{id}".format(id=self._name_id)
            self._name_id += 1

        trigger = self.smaug_client.triggers.create(name, type, properties)
        self.id = trigger.id
        return self.id

    def close(self):
        try:
            self.smaug_client.triggers.delete(self.id)
        except Exception:
            return


class Server(object):
    _name_id = 0

    def __init__(self):
        self.id = None
        self._name = None
        self.nova_client = base._get_nova_client_from_creds()
        self.cinder_client = base._get_cinder_client_from_creds()

    def _server_status(self, status=None):
        try:
            server = self.nova_client.servers.get(self.id)
        except Exception:
            return False

        if status is None or status == server.status:
            return True
        else:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "type": constants.SERVER_RESOURCE_TYPE,
            "name": self._name,
        }

    def create(self, name=None, image=DEFAULT_IMAGE, flavor=DEFAULT_FLAVOR,
               timeout=MEDIUM_TIMEOUT):
        image = self.nova_client.images.find(name=image)
        flavor = self.nova_client.flavors.find(name=flavor)
        if name is None:
            name = "SmaugFullstack-Server-{id}".format(id=self._name_id)
            self._name_id += 1
            self._name = name

        server = self.nova_client.servers.create(name=name, image=image,
                                                 flavor=flavor)
        self.id = server.id

        utils.wait_until_true(partial(self._server_status, 'ACTIVE'),
                              timeout=timeout, sleep=MEDIUM_SLEEP)
        return self.id

    def _volume_attached(self, volume_id):
        volume_item = self.cinder_client.volumes.get(volume_id)
        server_attachments = filter(lambda x: x['server_id'] == self.id,
                                    volume_item.attachments)
        if len(server_attachments) > 0:
            return True
        else:
            return False

    def attach_volume(self, volume_id, timeout=MEDIUM_TIMEOUT):
        self.nova_client.volumes.create_server_volume(self.id, volume_id)
        utils.wait_until_true(partial(self._volume_attached, volume_id),
                              timeout=timeout, sleep=MEDIUM_SLEEP)

    def close(self, timeout=MEDIUM_TIMEOUT):
        try:
            self.nova_client.servers.delete(self.id)
        except Exception:
            return
        utils.wait_until_none(self._server_status, timeout=timeout,
                              sleep=MEDIUM_SLEEP)


class Volume(object):
    _name_id = 0

    def __init__(self):
        self.id = None
        self._name = None
        self.cinder_client = base._get_cinder_client_from_creds()

    def _volume_status(self, status=None):
        try:
            volume = self.cinder_client.volumes.get(self.id)
        except Exception:
            return False

        if status is None or status == volume.status:
            return True
        else:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "type": constants.VOLUME_RESOURCE_TYPE,
            "name": self._name,
        }

    def create(self, size, name=None, timeout=MEDIUM_TIMEOUT):
        if name is None:
            name = "SmaugFullstack-Volume-{id}".format(id=self._name_id)
            self._name_id += 1

        self._name = name
        volume = self.cinder_client.volumes.create(size, name=name)
        self.id = volume.id
        utils.wait_until_true(partial(self._volume_status, 'available'),
                              timeout=timeout, sleep=MEDIUM_SLEEP)
        return self.id

    def close(self, timeout=MEDIUM_TIMEOUT):
        try:
            self.cinder_client.volumes.delete(self.id)
        except Exception:
            return
        utils.wait_until_none(self._volume_status, timeout=timeout,
                              sleep=MEDIUM_SLEEP)
