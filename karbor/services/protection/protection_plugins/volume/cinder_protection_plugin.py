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
from karbor.common import constants
from karbor import exception
from karbor.i18n import _LE, _LI
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.volume \
    import volume_plugin_cinder_schemas as cinder_schemas
from karbor.services.protection.restore_heat import HeatResource
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from oslo_utils import uuidutils

LOG = logging.getLogger(__name__)

cinder_backup_opts = [
    cfg.IntOpt('poll_interval', default=30,
               help='Poll interval for Cinder backup status'),
]

CONF = cfg.CONF
CONF.register_opts(cinder_backup_opts, 'cinder_backup_protection_plugin')


def status_poll(get_status_func, interval, success_statuses=set(),
                failure_statuses=set(), ignore_statuses=set(),
                ignore_unexpected=False):
    def _poll():
        status = get_status_func()
        if status in success_statuses:
            raise loopingcall.LoopingCallDone(retvalue=True)
        if status in failure_statuses:
            raise loopingcall.LoopingCallDone(retvalue=False)
        if status in ignore_statuses:
            return
        if ignore_unexpected is False:
            raise loopingcall.LoopingCallDone(retvalue=False)

    loop = loopingcall.FixedIntervalLoopingCall(_poll)
    return loop.start(interval=interval, initial_delay=interval).wait()


def get_backup_status(cinder_client, backup_id):
    LOG.debug('Polling backup (id: %s)', backup_id)
    try:
        backup = cinder_client.backups.get(backup_id)
        status = backup.status
    except cinder_exc.NotFound:
        status = 'not-found'
    LOG.debug('Polled backup (id: %(backup_id)s) status: %(status)s',
              {'backup_id': backup_id, 'status': status})
    return status


def get_volume_status(cinder_client, volume_id):
    LOG.debug('Polling volume (id: %s)', volume_id)
    try:
        volume = cinder_client.volumes.get(volume_id)
        status = volume.status
    except cinder_exc.NotFound:
        status = 'not-found'
    LOG.debug('Polled volume (id: %(volume_id)s) status: %(status)s',
              {'volume_id': volume_id, 'status': status})
    return status


class ProtectOperation(protection_plugin.Operation):
    def __init__(self):
        super(ProtectOperation, self).__init__()
        self._interval = CONF.cinder_backup_protection_plugin.poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(volume_id)
        cinder_client = ClientFactory.create_client('cinder', context)
        LOG.info(_LI('creating volume backup, volume_id: %s'), volume_id)
        bank_section.create_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        resource_metadata = {
            'volume_id': volume_id,
        }
        is_success = status_poll(
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
            raise exception.CreateBackupFailed(
                reason='Volume is in errorneous state',
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

        backup_name = parameters.get('backup_name')
        backup = None
        try:
            backup = cinder_client.backups.create(
                volume_id=volume_id,
                name=backup_name,
                force=True,
            )
        except Exception as e:
            LOG.error(_LE('Error creating backup (volume_id: %(volume_id)s): '
                          '%(reason)s'),
                      {'volume_id': volume_id, 'reason': e})
            bank_section.create_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise

        backup_id = backup.id
        resource_metadata['backup_id'] = backup_id
        bank_section.create_object('metadata', resource_metadata)

        is_success = status_poll(
            partial(get_backup_status, cinder_client, backup_id),
            interval=self._interval,
            success_statuses={'available'},
            failure_statuses={'error'},
            ignore_statuses={'creating'},
        )

        if is_success is True:
            LOG.info(
                _LI('protecting volume (id: %(volume_id)s) to backup '
                    '(id: %(backup_id)s) completed successfully'),
                {'backup_id': backup_id, 'volume_id': volume_id}
            )
            bank_section.create_object('status',
                                       constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = None
            try:
                backup = cinder_client.backups.get(backup_id)
            except Exception:
                reason = 'Unable to find backup'
            else:
                reason = backup.fail_reason
            LOG.error(
                _LE('protecting volume (id: %(volume_id)s) to backup '
                    '(id: %(backup_id)s) failed. Reason: "%(reason)s"'),
                {
                    'backup_id': backup_id,
                    'volume_id': volume_id,
                    'reason': reason,
                }
            )
            bank_section.create_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateBackupFailed(
                reason=reason,
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )


class RestoreOperation(protection_plugin.Operation):
    def __init__(self):
        super(RestoreOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, heat_template,
                **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        resource_metadata = bank_section.get_object('metadata')
        name = parameters.get('restore_name',
                              '%s@%s' % (checkpoint.id, resource_id))
        heat_resource_id = uuidutils.generate_uuid()
        heat_resource = HeatResource(heat_resource_id,
                                     constants.VOLUME_RESOURCE_TYPE)
        heat_resource.set_property('name', name)
        if 'restore_description' in parameters:
            heat_resource.set_property('description',
                                       parameters['restore_description'])

        heat_resource.set_property('backup_id', resource_metadata['backup_id'])
        heat_template.put_resource(resource_id, heat_resource)


class DeleteOperation(protection_plugin.Operation):
    def __init__(self):
        super(DeleteOperation, self).__init__()
        self._interval = CONF.cinder_backup_protection_plugin.poll_interval

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
                LOG.info(_LI('Backup id: %s not found. Assuming deleted'),
                         backup_id)
            is_success = status_poll(
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
            LOG.error(_LE('delete volume backup failed, backup_id: %s'),
                      backup_id)
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
        return ProtectOperation()

    def get_restore_operation(self, resource):
        return RestoreOperation()

    def get_delete_operation(self, resource):
        return DeleteOperation()
