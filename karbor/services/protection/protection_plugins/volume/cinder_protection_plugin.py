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
    import volume_plugin_cinder_schemas as cinder_schemas


LOG = logging.getLogger(__name__)

cinder_backup_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Cinder backup status'
    ),
    cfg.BoolOpt(
        'backup_from_snapshot', default=True,
        help='First take a snapshot of the volume, and backup from '
        'it. Minimizes the time the volume is unavailable.'
    ),
]


def get_backup_status(cinder_client, backup_id):
    return get_resource_status(cinder_client.backups, backup_id, 'backup')


def get_volume_status(cinder_client, volume_id):
    return get_resource_status(cinder_client.volumes, volume_id, 'volume')


def get_snapshot_status(cinder_client, snapshot_id):
    return get_resource_status(cinder_client.volume_snapshots, snapshot_id,
                               'snapshot')


def get_resource_status(resource_manager, resource_id, resource_type):
    LOG.debug('Polling %(resource_type)s (id: %(resource_id)s)', {
        'resource_type': resource_type,
        'resource_id': resource_id,
    })
    try:
        resource = resource_manager.get(resource_id)
        status = resource.status
    except cinder_exc.NotFound:
        status = 'not-found'
    LOG.debug(
        'Polled %(resource_type)s (id: %(resource_id)s) status: %(status)s',
        {
            'resource_type': resource_type,
            'resource_id': resource_id,
            'status': status
        }
    )
    return status


class ProtectOperation(protection_plugin.Operation):
    def __init__(self, poll_interval, backup_from_snapshot):
        super(ProtectOperation, self).__init__()
        self._interval = poll_interval
        self._backup_from_snapshot = backup_from_snapshot
        self.snapshot_id = None

    def _create_snapshot(self, cinder_client, volume_id):
        snapshot = cinder_client.volume_snapshots.create(volume_id, force=True)

        snapshot_id = snapshot.id
        is_success = utils.status_poll(
            partial(get_snapshot_status, cinder_client, snapshot_id),
            interval=self._interval,
            success_statuses={'available', },
            failure_statuses={'error', 'error_deleting', 'deleting',
                              'not-found'},
            ignore_statuses={'creating', },
        )
        if not is_success:
            raise Exception

        return snapshot_id

    def _delete_snapshot(self, cinder_client, snapshot_id):
        LOG.info('Cleaning up snapshot (snapshot_id: %s)', snapshot_id)
        cinder_client.volume_snapshots.delete(snapshot_id)
        return utils.status_poll(
            partial(get_snapshot_status, cinder_client, snapshot_id),
            interval=self._interval,
            success_statuses={'not-found', },
            failure_statuses={'error', 'error_deleting', 'creating'},
            ignore_statuses={'deleting', },
        )

    def _create_backup(self, cinder_client, volume_id, backup_name,
                       description, snapshot_id=None, incremental=False,
                       container=None, force=False):
        backup = cinder_client.backups.create(
            volume_id=volume_id,
            name=backup_name,
            description=description,
            force=force,
            snapshot_id=snapshot_id,
            incremental=incremental,
            container=container
        )

        backup_id = backup.id
        is_success = utils.status_poll(
            partial(get_backup_status, cinder_client, backup_id),
            interval=self._interval,
            success_statuses={'available'},
            failure_statuses={'error'},
            ignore_statuses={'creating'},
        )

        if not is_success:
            try:
                backup = cinder_client.backups.get(backup_id)
            except Exception:
                reason = 'Unable to find backup'
            else:
                reason = backup.fail_reason
            raise Exception(reason)

        return backup_id

    def on_prepare_finish(self, checkpoint, resource, context, parameters,
                          **kwargs):
        volume_id = resource.id
        if not self._backup_from_snapshot:
            LOG.info('Skipping taking snapshot of volume %s - backing up '
                     'directly', volume_id)
            return

        LOG.info('Taking snapshot of volume %s', volume_id)
        bank_section = checkpoint.get_resource_bank_section(volume_id)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        cinder_client = ClientFactory.create_client('cinder', context)
        try:
            self.snapshot_id = self._create_snapshot(cinder_client, volume_id)
        except Exception:
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason='Error creating snapshot for volume',
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(volume_id)
        cinder_client = ClientFactory.create_client('cinder', context)
        LOG.info('creating volume backup, volume_id: %s', volume_id)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        resource_metadata = {
            'volume_id': volume_id,
        }
        is_success = utils.status_poll(
            partial(get_volume_status, cinder_client, volume_id),
            interval=self._interval,
            success_statuses={'available', 'in-use', 'error_extending',
                              'error_restoring'},
            failure_statuses={'error', 'error_deleting', 'deleting',
                              'not-found'},
            ignore_statuses={'attaching', 'creating', 'backing-up',
                             'restoring-backup'},
        )
        if not is_success:
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason='Volume is in erroneous state',
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

        backup_name = parameters.get('backup_name', None)
        description = parameters.get('description', None)
        backup_mode = parameters.get('backup_mode', "full")
        container = parameters.get('container', None)
        force = parameters.get('force', False)
        incremental = False
        if backup_mode == "incremental":
            incremental = True
        elif backup_mode == "full":
            incremental = False

        try:
            backup_id = self._create_backup(cinder_client, volume_id,
                                            backup_name, description,
                                            self.snapshot_id,
                                            incremental, container, force)
        except Exception as e:
            LOG.error('Error creating backup (volume_id: %(volume_id)s '
                      'snapshot_id: %(snapshot_id)s): %(reason)s',
                      {'volume_id': volume_id,
                       'snapshot_id': self.snapshot_id,
                       'reason': e}
                      )
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=e,
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

        resource_metadata['backup_id'] = backup_id
        bank_section.update_object('metadata', resource_metadata)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_AVAILABLE)
        LOG.info('Backed up volume (volume_id: %(volume_id)s snapshot_id: '
                 '%(snapshot_id)s backup_id: %(backup_id)s) successfully',
                 {'backup_id': backup_id,
                  'snapshot_id': self.snapshot_id,
                  'volume_id': volume_id}
                 )

        if self.snapshot_id:
            try:
                self._delete_snapshot(cinder_client, self.snapshot_id)
            except Exception as e:
                LOG.warning('Failed deleting snapshot: %(snapshot_id)s. '
                            'Reason: %(reason)s',
                            {'snapshot_id': self.snapshot_id, 'reason': e})


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        resource_metadata = bank_section.get_object('metadata')
        cinder_client = ClientFactory.create_client('cinder', context)

        # create volume
        volume_property = {
            'name': parameters.get(
                'restore_name',  '%s@%s' % (checkpoint.id, resource_id))
        }
        if 'restore_description' in parameters:
            volume_property['description'] = parameters['restore_description']
        backup_id = resource_metadata['backup_id']
        try:
            volume_id = cinder_client.restores.restore(backup_id).volume_id
            cinder_client.volumes.update(volume_id, **volume_property)
        except Exception as ex:
            LOG.error('Error creating volume (backup_id: %(backup_id)s): '
                      '%(reason)s',
                      {'backup_id': backup_id,
                       'reason': ex})
            raise

        # check and update status
        update_method = partial(
            utils.update_resource_restore_result,
            kwargs.get('restore'), resource.type, volume_id)

        update_method(constants.RESOURCE_STATUS_RESTORING)

        is_success = self._check_create_complete(cinder_client, volume_id)
        if is_success:
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
            kwargs.get("heat_template").put_parameter(resource_id, volume_id)
        else:
            reason = 'Error creating volume'
            update_method(constants.RESOURCE_STATUS_ERROR, reason)

            raise exception.RestoreBackupFailed(
                reason=reason,
                resource_id=resource_id,
                resource_type=resource.type
            )

    def _check_create_complete(self, cinder_client, volume_id):
        return utils.status_poll(
            partial(get_volume_status, cinder_client, volume_id),
            interval=self._interval,
            success_statuses={'available'},
            failure_statuses={'error', 'not-found'},
            ignore_statuses={'creating', 'restoring-backup', 'downloading'},
        )


class DeleteOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(DeleteOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        backup_id = None
        try:
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_DELETING)
            resource_metadata = bank_section.get_object('metadata')
            backup_id = resource_metadata['backup_id']
            cinder_client = ClientFactory.create_client('cinder', context)
            try:
                backup = cinder_client.backups.get(backup_id)
                cinder_client.backups.delete(backup)
            except cinder_exc.NotFound:
                LOG.info('Backup id: %s not found. Assuming deleted',
                         backup_id)
            is_success = utils.status_poll(
                partial(get_backup_status, cinder_client, backup_id),
                interval=self._interval,
                success_statuses={'deleted', 'not-found'},
                failure_statuses={'error', 'error_deleting'},
                ignore_statuses={'deleting'},
            )
            if not is_success:
                raise exception.NotFound()
            bank_section.delete_object('metadata')
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_DELETED)
        except Exception as e:
            LOG.error('delete volume backup failed, backup_id: %s', backup_id)
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteBackupFailed(
                reason=six.text_type(e),
                resource_id=resource_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE
            )


class CinderBackupProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.VOLUME_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(CinderBackupProtectionPlugin, self).__init__(config)
        self._config.register_opts(cinder_backup_opts,
                                   'cinder_backup_protection_plugin')
        self._plugin_config = self._config.cinder_backup_protection_plugin
        self._poll_interval = self._plugin_config.poll_interval
        self._backup_from_snapshot = self._plugin_config.backup_from_snapshot

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resources_type):
        return cinder_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resources_type):
        return cinder_schemas.RESTORE_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resources_type):
        return cinder_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        # TODO(hurong)
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._poll_interval,
                                self._backup_from_snapshot)

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_delete_operation(self, resource):
        return DeleteOperation(self._poll_interval)
