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

from functools import partial
import six

from cinderclient import exceptions as cinder_exc
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins import utils
from karbor.services.protection.protection_plugins.volume \
    import volume_snapshot_plugin_schemas as volume_schemas

LOG = logging.getLogger(__name__)

volume_snapshot_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Cinder volume status.'
    )
]

VOLUME_FAILURE_STATUSES = {'error', 'error_deleting', 'deleting',
                           'not-found'}

VOLUME_IGNORE_STATUSES = {'attaching', 'creating', 'backing-up',
                          'restoring-backup'}


def get_snapshot_status(cinder_client, snapshot_id):
    return get_resource_status(cinder_client.volume_snapshots, snapshot_id,
                               'snapshot')


def get_volume_status(cinder_client, volume_id):
    return get_resource_status(cinder_client.volumes, volume_id, 'volume')


def get_resource_status(resource_manager, resource_id, resource_type):
    LOG.debug('Polling %(resource_type)s (id: %(resource_id)s)',
              {'resource_type': resource_type, 'resource_id': resource_id})
    try:
        resource = resource_manager.get(resource_id)
        status = resource.status
    except cinder_exc.NotFound:
        status = 'not-found'
    LOG.debug(
        'Polled %(resource_type)s (id: %(resource_id)s) status: %(status)s',
        {'resource_type': resource_type, 'resource_id': resource_id,
         'status': status}
    )
    return status


class ProtectOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(ProtectOperation, self).__init__()
        self._interval = poll_interval

    def _create_snapshot(self, cinder_client, volume_id, snapshot_name,
                         description, force):
        snapshot = cinder_client.volume_snapshots.create(
            volume_id=volume_id,
            name=snapshot_name,
            description=description,
            force=force
        )

        snapshot_id = snapshot.id
        is_success = utils.status_poll(
            partial(get_snapshot_status, cinder_client, snapshot_id),
            interval=self._interval,
            success_statuses={'available'},
            failure_statuses={'error', 'error_deleting', 'deleting',
                              'not-found'},
            ignore_statuses={'creating'},
            ignore_unexpected=True
        )

        if not is_success:
            try:
                snapshot = cinder_client.volume_snapshots.get(snapshot_id)
            except Exception:
                reason = 'Unable to find volume snapshot.'
            else:
                reason = 'The status of snapshot is %s' % snapshot.status
            raise exception.CreateResourceFailed(
                name="Volume Snapshot",
                reason=reason, resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE)

        return snapshot_id

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(volume_id)
        cinder_client = ClientFactory.create_client('cinder', context)
        LOG.info('Creating volume snapshot, volume_id: %s', volume_id)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        volume_info = cinder_client.volumes.get(volume_id)
        is_success = utils.status_poll(
            partial(get_volume_status, cinder_client, volume_id),
            interval=self._interval,
            success_statuses={'available', 'in-use', 'error_extending',
                              'error_restoring'},
            failure_statuses=VOLUME_FAILURE_STATUSES,
            ignore_statuses=VOLUME_IGNORE_STATUSES,
        )
        if not is_success:
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Volume Snapshot",
                reason='Volume is in a error status.',
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )
        resource_metadata = {
            'volume_id': volume_id,
            'size': volume_info.size
        }
        snapshot_name = parameters.get('snapshot_name', None)
        description = parameters.get('description', None)
        force = parameters.get('force', False)
        try:
            snapshot_id = self._create_snapshot(cinder_client, volume_id,
                                                snapshot_name,
                                                description, force)
        except Exception as e:
            LOG.error('Error creating snapshot (volume_id: %(volume_id)s '
                      ': %(reason)s', {'volume_id': volume_id, 'reason': e})
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Volume Snapshot",
                reason=e, resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

        resource_metadata['snapshot_id'] = snapshot_id
        bank_section.update_object('metadata', resource_metadata)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_AVAILABLE)
        LOG.info('Snapshot volume (volume_id: %(volume_id)s snapshot_id: '
                 '%(snapshot_id)s ) successfully',
                 {'volume_id': volume_id, 'snapshot_id': snapshot_id})


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(original_volume_id)
        cinder_client = ClientFactory.create_client('cinder', context)
        resource_metadata = bank_section.get_object('metadata')
        restore_name = parameters.get('restore_name',
                                      'volume-%s@%s' % (checkpoint.id,
                                                        original_volume_id))
        restore_description = parameters.get('restore_description', None)
        snapshot_id = resource_metadata['snapshot_id']
        size = resource_metadata['size']
        restore = kwargs.get('restore')
        LOG.info("Restoring a volume from snapshot, "
                 "original_volume_id: %s", original_volume_id)
        try:
            volume = cinder_client.volumes.create(
                size, snapshot_id=snapshot_id,
                name=restore_name,
                description=restore_description)
            is_success = utils.status_poll(
                partial(get_volume_status, cinder_client, volume.id),
                interval=self._interval,
                success_statuses={'available', 'in-use', 'error_extending',
                                  'error_restoring'},
                failure_statuses=VOLUME_FAILURE_STATUSES,
                ignore_statuses=VOLUME_IGNORE_STATUSES,
            )
            if is_success is not True:
                LOG.error('The status of volume is invalid. status:%s',
                          volume.status)
                reason = 'Invalid status: %s' % volume.status
                restore.update_resource_status(
                    constants.VOLUME_RESOURCE_TYPE,
                    volume.id, volume.status, reason)
                restore.save()
                raise exception.RestoreResourceFailed(
                    name="Volume Snapshot",
                    resource_id=original_volume_id,
                    resource_type=constants.VOLUME_RESOURCE_TYPE)
            restore.update_resource_status(constants.VOLUME_RESOURCE_TYPE,
                                           volume.id, volume.status)
            restore.save()
        except Exception as e:
            LOG.error("Restore volume from snapshot failed, volume_id: %s",
                      original_volume_id)
            raise exception.RestoreResourceFailed(
                name="Volume Snapshot",
                reason=e, resource_id=original_volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE)
        LOG.info("Finish restoring a volume from snapshot, volume_id: %s",
                 original_volume_id)


class DeleteOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(DeleteOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        snapshot_id = None
        try:
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_DELETING)
            resource_metadata = bank_section.get_object('metadata')
            snapshot_id = resource_metadata['snapshot_id']
            cinder_client = ClientFactory.create_client('cinder', context)
            try:
                snapshot = cinder_client.volume_snapshots.get(snapshot_id)
                cinder_client.volume_snapshots.delete(snapshot)
            except cinder_exc.NotFound:
                LOG.info('Snapshot id: %s not found. Assuming deleted',
                         snapshot_id)
            is_success = utils.status_poll(
                partial(get_snapshot_status, cinder_client, snapshot_id),
                interval=self._interval,
                success_statuses={'deleted', 'not-found'},
                failure_statuses={'error', 'error_deleting'},
                ignore_statuses={'deleting'},
                ignore_unexpected=True
            )
            if not is_success:
                raise exception.NotFound()
            bank_section.delete_object('metadata')
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_DELETED)
        except Exception as e:
            LOG.error('Delete volume snapshot failed, snapshot_id: %s',
                      snapshot_id)
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Volume Snapshot",
                reason=six.text_type(e),
                resource_id=resource_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE
            )


class VolumeSnapshotProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.VOLUME_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(VolumeSnapshotProtectionPlugin, self).__init__(config)
        self._config.register_opts(volume_snapshot_opts,
                                   'volume_snapshot_plugin')
        self._plugin_config = self._config.volume_snapshot_plugin
        self._poll_interval = self._plugin_config.poll_interval

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resources_type):
        return volume_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resources_type):
        return volume_schemas.RESTORE_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resources_type):
        return volume_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._poll_interval)

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_delete_operation(self, resource):
        return DeleteOperation(self._poll_interval)
