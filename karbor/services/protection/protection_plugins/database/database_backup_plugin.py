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

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.database \
    import database_backup_plugin_schemas as database_instance_schemas
from karbor.services.protection.protection_plugins import utils
from oslo_config import cfg
from oslo_log import log as logging
from troveclient import exceptions as trove_exc

LOG = logging.getLogger(__name__)

trove_backup_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Trove Database Instance status.'
    )
]

DATABASE_FAILURE_STATUSES = {'BLOCKED', 'FAILED', 'REBOOT',
                             'SHUTDOWN', 'ERROR',
                             'RESTART_REQUIRED', 'EJECT', 'DETACH'}

DATABASE_IGNORE_STATUSES = {'BUILD', 'RESIZE', 'BACKUP', 'PROMOTE', 'UPGRADE'}


def get_backup_status(trove_client, backup_id):
    return get_resource_status(trove_client.backups, backup_id,
                               'backup')


def get_database_instance_status(trove_client, instance_id):
    return get_resource_status(trove_client.instances, instance_id, 'instance')


def get_resource_status(resource_manager, resource_id, resource_type):
    LOG.debug('Polling %(resource_type)s (id: %(resource_id)s)',
              {'resource_type': resource_type, 'resource_id': resource_id})
    try:
        resource = resource_manager.get(resource_id)
        status = resource.status
    except trove_exc.NotFound:
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

    def _create_backup(self, trove_client, instance_id, backup_name,
                       description):
        backup = trove_client.backups.create(
            backup_name,
            instance=instance_id,
            description=description
        )

        backup_id = backup.id
        is_success = utils.status_poll(
            partial(get_backup_status, trove_client, backup_id),
            interval=self._interval,
            success_statuses={'COMPLETED'},
            failure_statuses={'FAILED'},
            ignore_statuses={'BUILDING'},
            ignore_unexpected=True
        )

        if not is_success:
            try:
                backup = trove_client.backups.get(backup_id)
            except Exception:
                reason = 'Unable to find backup.'
            else:
                reason = 'The status of backup is %s' % backup.status
            raise exception.CreateResourceFailed(
                name="Database Instance Backup",
                reason=reason, resource_id=instance_id,
                resource_type=constants.DATABASE_RESOURCE_TYPE)

        return backup_id

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        instance_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(instance_id)
        trove_client = ClientFactory.create_client('trove', context)
        LOG.info('creating database instance backup, instance_id: %s',
                 instance_id)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        instance_info = trove_client.instances.get(instance_id)
        if instance_info.status != "ACTIVE":
            is_success = utils.status_poll(
                partial(get_database_instance_status, trove_client,
                        instance_id),
                interval=self._interval, success_statuses={'ACTIVE'},
                failure_statuses=DATABASE_FAILURE_STATUSES,
                ignore_statuses=DATABASE_IGNORE_STATUSES,
            )
            if not is_success:
                bank_section.update_object('status',
                                           constants.RESOURCE_STATUS_ERROR)
                raise exception.CreateResourceFailed(
                    name="Database instance Backup",
                    reason='Database instance is in a error status.',
                    resource_id=instance_id,
                    resource_type=constants.DATABASE_RESOURCE_TYPE,
                )
        resource_metadata = {
            'instance_id': instance_id,
            'datastore': instance_info.datastore,
            'flavor': instance_info.flavor,
            'size': instance_info.volume['size'],
        }
        backup_name = parameters.get('backup_name', 'backup%s' % (
            instance_id))
        description = parameters.get('description', None)
        try:
            backup_id = self._create_backup(
                trove_client, instance_id, backup_name, description)
        except exception.CreateResourceFailed as e:
            LOG.error('Error creating backup (instance_id: %(instance_id)s '
                      ': %(reason)s', {'instance_id': instance_id,
                                       'reason': e})
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise

        resource_metadata['backup_id'] = backup_id

        bank_section.update_object('metadata', resource_metadata)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_AVAILABLE)
        LOG.info('Backup database instance (instance_id: %(instance_id)s '
                 'backup_id: %(backup_id)s ) successfully',
                 {'instance_id': instance_id, 'backup_id': backup_id})


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_instance_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(
            original_instance_id)
        trove_client = ClientFactory.create_client('trove', context)
        resource_metadata = bank_section.get_object('metadata')
        restore_name = parameters.get('restore_name',
                                      '%s@%s' % (checkpoint.id,
                                                 original_instance_id))
        flavor = resource_metadata['flavor']
        size = resource_metadata['size']
        backup_id = resource_metadata['backup_id']
        restore = kwargs.get('restore')
        LOG.info("Restoring a database instance from backup, "
                 "original_instance_id: %s.", original_instance_id)

        try:
            instance_info = trove_client.instances.create(
                restore_name, flavor["id"], volume={"size": size},
                restorePoint={"backupRef": backup_id})
            is_success = utils.status_poll(
                partial(get_database_instance_status, trove_client,
                        instance_info.id),
                interval=self._interval, success_statuses={'ACTIVE'},
                failure_statuses=DATABASE_FAILURE_STATUSES,
                ignore_statuses=DATABASE_IGNORE_STATUSES
            )
            if is_success is not True:
                LOG.error('The status of database instance is '
                          'invalid. status:%s', instance_info.status)
                restore.update_resource_status(
                    constants.DATABASE_RESOURCE_TYPE,
                    instance_info.id, instance_info.status,
                    "Invalid status.")
                restore.save()
                raise exception.RestoreResourceFailed(
                    name="Database instance Backup",
                    reason="Invalid status.",
                    resource_id=original_instance_id,
                    resource_type=constants.DATABASE_RESOURCE_TYPE)
            restore.update_resource_status(
                constants.DATABASE_RESOURCE_TYPE,
                instance_info.id, instance_info.status)
            restore.save()
        except Exception as e:
            LOG.error("Restore Database instance from backup "
                      "failed, instance_id: %s.", original_instance_id)
            raise exception.RestoreResourceFailed(
                name="Database instance Backup",
                reason=e, resource_id=original_instance_id,
                resource_type=constants.DATABASE_RESOURCE_TYPE)
        LOG.info("Finish restoring a Database instance from backup,"
                 "instance_id: %s.", original_instance_id)


class VerifyOperation(protection_plugin.Operation):
    def __init__(self):
        super(VerifyOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_instance_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(
            original_instance_id)
        trove_client = ClientFactory.create_client('trove', context)
        resource_metadata = bank_section.get_object('metadata')
        LOG.info('Verifying the database instance, instance_id: %s',
                 original_instance_id)

        update_method = partial(
            utils.update_resource_verify_result,
            kwargs.get('verify'), resource.type, original_instance_id)

        backup_id = resource_metadata['backup_id']
        try:
            instance_backup = trove_client.backups.get(backup_id)
            backup_status = instance_backup.status
        except Exception as ex:
            LOG.error('Getting database backup (backup_id: %(backup_id)s):'
                      '%(reason)s fails',
                      {'backup_id': backup_id, 'reason': ex})
            reason = 'Getting database backup fails.'
            update_method(constants.RESOURCE_STATUS_ERROR, reason)
            raise

        if backup_status == 'COMPLETED':
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = ('The status of database backup status is %s.'
                      % backup_status)
            update_method(backup_status, reason)
            raise exception.VerifyResourceFailed(
                name="Database backup",
                reason=reason,
                resource_id=original_instance_id,
                resource_type=resource.type)


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
            trove_client = ClientFactory.create_client('trove', context)
            try:
                backup = trove_client.backups.get(backup_id)
                trove_client.backups.delete(backup)
            except trove_exc.NotFound:
                LOG.info('Backup id: %s not found. Assuming deleted',
                         backup_id)
            is_success = utils.status_poll(
                partial(get_backup_status, trove_client, backup_id),
                interval=self._interval,
                success_statuses={'not-found'},
                failure_statuses={'FAILED', 'DELETE_FAILED'},
                ignore_statuses={'COMPLETED'},
                ignore_unexpected=True
            )
            if not is_success:
                raise exception.NotFound()
            bank_section.delete_object('metadata')
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_DELETED)
        except Exception as e:
            LOG.error('Delete Database instance Backup failed, backup_id: %s',
                      backup_id)
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Database instance Backup",
                reason=six.text_type(e),
                resource_id=resource_id,
                resource_type=constants.DATABASE_RESOURCE_TYPE
            )


class DatabaseBackupProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.DATABASE_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(DatabaseBackupProtectionPlugin, self).__init__(config)
        self._config.register_opts(trove_backup_opts,
                                   'database_backup_plugin')
        self._plugin_config = self._config.database_backup_plugin
        self._poll_interval = self._plugin_config.poll_interval

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resources_type):
        return database_instance_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resources_type):
        return database_instance_schemas.RESTORE_SCHEMA

    @classmethod
    def get_verify_schema(cls, resources_type):
        return database_instance_schemas.VERIFY_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resources_type):
        return database_instance_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._poll_interval)

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_verify_operation(self, resource):
        return VerifyOperation()

    def get_delete_operation(self, resource):
        return DeleteOperation(self._poll_interval)
