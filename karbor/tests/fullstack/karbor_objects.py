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

from karbor.common import constants
from karbor.tests.fullstack import karbor_base as base
from karbor.tests.fullstack import utils

SHORT_TIMEOUT = 150
MEDIUM_TIMEOUT = 450
LONG_TIMEOUT = 900

SHORT_SLEEP = 3
MEDIUM_SLEEP = 15
LONG_SLEEP = 30
HUGE_SLEEP = 100

DEFAULT_FLAVOR = "cirros256"
DEFAULT_NETWORK = "private"


class Checkpoint(object):
    def __init__(self):
        super(Checkpoint, self).__init__()
        self.id = None
        self._provider_id = None
        self.karbor_client = base._get_karbor_client()

    def _checkpoint_status(self, status=None):
        try:
            cp = self.karbor_client.checkpoints.get(self._provider_id, self.id)
        except Exception:
            return False

        if status is None or cp.status == status:
            return True
        else:
            return False

    def create(self, provider_id, plan_id, timeout=LONG_TIMEOUT):
        self._provider_id = provider_id
        checkpoint = self.karbor_client.checkpoints.create(provider_id,
                                                           plan_id)
        self.id = checkpoint.id
        utils.wait_until_true(partial(self._checkpoint_status,
                                      constants.CHECKPOINT_STATUS_AVAILABLE),
                              timeout=timeout, sleep=HUGE_SLEEP)
        return self.id

    def close(self, timeout=MEDIUM_TIMEOUT):
        try:
            self.karbor_client.checkpoints.delete(self._provider_id, self.id)
        except Exception:
            return
        utils.wait_until_true(partial(self._checkpoint_status,
                                      constants.CHECKPOINT_STATUS_DELETED),
                              timeout=timeout, sleep=LONG_SLEEP)


class Plan(object):
    _name_id = 0

    def __init__(self):
        super(Plan, self).__init__()
        self.id = None
        self.karbor_client = base._get_karbor_client()

    def create(self, provider_id, resources,
               parameters={}, name=None):
        def _transform_resource(resource):
            if isinstance(resource, dict):
                return resource
            if hasattr(resource, 'to_dict') and callable(resource.to_dict):
                return resource.to_dict()

        if name is None:
            name = "KarborFullstack-Plan-{id}".format(
                id=self.__class__._name_id
            )
            self.__class__._name_id += 1

        resources = map(_transform_resource, resources)
        plan = self.karbor_client.plans.create(name, provider_id, resources,
                                               parameters)
        self.id = plan.id
        return self.id

    def update(self, data):
        return self.karbor_client.plans.update(self.id, data)

    def close(self):
        try:
            self.karbor_client.plans.delete(self.id)
        except Exception:
            return


class Restore(object):
    def __init__(self):
        super(Restore, self).__init__()
        self.id = None
        self.karbor_client = base._get_karbor_client()

    def _restore_status(self, status=None):
        try:
            restore = self.karbor_client.restores.get(self.id)
        except Exception:
            return False

        if status is None or restore.status == status:
            return True
        else:
            return False

    def create(self, provider_id, checkpoint_id, target, parameters,
               restore_auth, timeout=LONG_TIMEOUT):
        restore = self.karbor_client.restores.create(provider_id,
                                                     checkpoint_id,
                                                     target,
                                                     parameters,
                                                     restore_auth)
        self.id = restore.id
        utils.wait_until_true(partial(self._restore_status, 'success'),
                              timeout=timeout, sleep=HUGE_SLEEP)
        return self.id

    def close(self):
        pass


class Trigger(object):
    _name_id = 0

    def __init__(self):
        super(Trigger, self).__init__()
        self.id = None
        self.karbor_client = base._get_karbor_client()

    def create(self, type, properties, name=None):
        if name is None:
            name = "KarborFullstack-Trigger-{id}".format(
                id=self.__class__._name_id
            )
            self.__class__._name_id += 1

        trigger = self.karbor_client.triggers.create(name, type, properties)
        self.id = trigger.id
        return self.id

    def close(self):
        try:
            self.karbor_client.triggers.delete(self.id)
        except Exception:
            return


class ScheduledOperation(object):
    _name_id = 0

    def __init__(self):
        super(ScheduledOperation, self).__init__()
        self.id = None
        self.karbor_client = base._get_karbor_client()

    def create(self, operation_type, trigger_id,
               operation_definition, name=None):
        if name is None:
            name = "KarborFullstack-Scheduled-Operation-{id}".format(
                id=self.__class__._name_id
            )
            self.__class__._name_id += 1

        scheduled_operation = self.karbor_client.scheduled_operations.create(
            name,
            operation_type,
            trigger_id,
            operation_definition
        )
        self.id = scheduled_operation.id
        return self.id

    def close(self):
        try:
            self.karbor_client.scheduled_operations.delete(self.id)
        except Exception:
            return


class Server(object):
    _name_id = 0

    def __init__(self):
        super(Server, self).__init__()
        self.id = None
        self._name = None
        self.nova_client = base._get_nova_client()
        self.neutron_client = base._get_neutron_client()
        self.cinder_client = base._get_cinder_client()
        self.glance_client = base._get_glance_client()

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

    def create(self, name=None, image=None, volume=None, flavor=DEFAULT_FLAVOR,
               network=DEFAULT_NETWORK, timeout=LONG_TIMEOUT):
        block_device_mapping_v2 = None
        if volume:
            block_device_mapping_v2 = [{
                'uuid': volume,
                'source_type': 'volume',
                'destination_type': 'volume',
                'boot_index': 0,
                'delete_on_termination': False}]
        else:
            if not image:
                images = self.glance_client.images.list()
                for image_iter in images:
                    if image_iter['disk_format'] not in ('aki', 'ari') and (
                            image_iter['name'].startswith('cirros')):
                        image = image_iter['id']
                        break
            assert image
        flavor = self.nova_client.flavors.find(name=flavor)
        if name is None:
            name = "KarborFullstack-Server-{id}".format(
                id=self.__class__._name_id
            )
            self.__class__._name_id += 1
            self._name = name

        networks = self.neutron_client.list_networks(name=network)
        assert len(networks['networks']) > 0
        network_id = networks['networks'][0]['id']

        server = self.nova_client.servers.create(
            name=name,
            image=image,
            block_device_mapping_v2=block_device_mapping_v2,
            flavor=flavor,
            nics=[{"net-id": network_id}],
        )
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
                              timeout=timeout, sleep=SHORT_SLEEP)

    def _volume_detached(self, volume_id):
        volume_item = self.cinder_client.volumes.get(volume_id)
        server_attachments = filter(lambda x: x['server_id'] == self.id,
                                    volume_item.attachments)
        if len(server_attachments) > 0:
            return False
        else:
            return True

    def detach_volume(self, volume_id, timeout=MEDIUM_TIMEOUT):
        self.nova_client.volumes.delete_server_volume(self.id, volume_id)
        utils.wait_until_true(partial(self._volume_detached, volume_id),
                              timeout=timeout, sleep=SHORT_SLEEP)

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
        super(Volume, self).__init__()
        self.id = None
        self._name = None
        self.cinder_client = base._get_cinder_client()
        self.glance_client = base._get_glance_client()

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
            "extra_info": {'availability_zone': 'az1'},
        }

    def create(self, size, name=None, create_from_image=False,
               timeout=LONG_TIMEOUT):
        if name is None:
            name = "KarborFullstack-Volume-{id}".format(
                id=self.__class__._name_id
            )
            self.__class__._name_id += 1

        self._name = name
        image = None
        if create_from_image:
            images = self.glance_client.images.list()
            for image_iter in images:
                if image_iter['disk_format'] not in ('aki', 'ari') and (
                        image_iter['name'].startswith('cirros')):
                    image = image_iter['id']
                    break
            assert image
        volume = self.cinder_client.volumes.create(size, name=name,
                                                   imageRef=image)
        self.id = volume.id
        utils.wait_until_true(partial(self._volume_status, 'available'),
                              timeout=timeout, sleep=MEDIUM_SLEEP)
        return self.id

    def close(self, timeout=LONG_TIMEOUT):
        try:
            self.cinder_client.volumes.delete(self.id)
        except Exception:
            return
        utils.wait_until_none(self._volume_status, timeout=timeout,
                              sleep=MEDIUM_SLEEP)


class Share(object):
    _name_id = 0

    def __init__(self):
        super(Share, self).__init__()
        self.id = None
        self._name = None
        self.manila_client = base._get_manila_client()
        self.neutron_client = base._get_neutron_client()

    def _share_status(self, status=None):
        try:
            share = self.manila_client.shares.get(self.id)
        except Exception:
            return False

        if status is None or status == share.status:
            return True
        else:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "type": constants.SHARE_RESOURCE_TYPE,
            "name": self._name,
        }

    def create(self, share_proto, size, name=None, timeout=LONG_TIMEOUT):
        if name is None:
            name = "KarborFullstack-Share-{id}".format(id=self._name_id)
            self._name_id += 1

        self._name = name
        share = self.manila_client.shares.create(share_proto, size, name=name)
        self.id = share.id
        utils.wait_until_true(partial(self._share_status, 'available'),
                              timeout=timeout, sleep=MEDIUM_SLEEP)
        return self.id

    def close(self, timeout=MEDIUM_TIMEOUT):
        try:
            self.manila_client.shares.delete(self.id)
        except Exception:
            return
        utils.wait_until_none(self._share_status, timeout=timeout,
                              sleep=MEDIUM_SLEEP)
