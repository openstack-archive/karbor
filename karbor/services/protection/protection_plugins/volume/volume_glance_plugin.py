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

from cinderclient import exceptions as cinder_exc
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins import utils
from karbor.services.protection.protection_plugins.volume \
    import volume_glance_plugin_schemas as volume_schemas

LOG = logging.getLogger(__name__)

volume_glance_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Cinder volume status.'
    ),
    cfg.BoolOpt(
        'backup_from_snapshot', default=True,
        help='First take a snapshot of the volume, and backup from '
        'it. Minimizes the time the volume is unavailable.'
    ),
    cfg.IntOpt('backup_image_object_size',
               default=65536*512,
               help='The size in bytes of temporary image objects. '
                    'The value must be a multiple of 65536('
                    'the size of image\'s chunk).'),
]

VOLUME_SUCCESS_STATUSES = {'available', 'in-use',
                           'error_extending', 'error_restoring'}

VOLUME_FAILURE_STATUSES = {'error', 'error_deleting', 'deleting',
                           'not-found'}

VOLUME_IGNORE_STATUSES = {'attaching', 'creating', 'backing-up',
                          'restoring-backup', 'uploading', 'downloading'}


def get_snapshot_status(cinder_client, snapshot_id):
    return get_resource_status(cinder_client.volume_snapshots, snapshot_id,
                               'snapshot')


def get_volume_status(cinder_client, volume_id):
    return get_resource_status(cinder_client.volumes, volume_id, 'volume')


def get_image_status(glance_client, image_id):
    LOG.debug('Polling image (image_id: %s)', image_id)
    try:
        status = glance_client.images.get(image_id)['status']
    except exception.NotFound:
        status = 'not-found'
    LOG.debug('Polled image (image_id: %s) status: %s',
              image_id, status)
    return status


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
    def __init__(self, poll_interval, backup_from_snapshot, image_object_size):
        super(ProtectOperation, self).__init__()
        self._interval = poll_interval
        self._backup_from_snapshot = backup_from_snapshot
        self._image_object_size = image_object_size

    def _create_snapshot(self, cinder_client, volume_id):
        LOG.info("Start creating snapshot of volume({0}).".format(volume_id))
        snapshot = cinder_client.volume_snapshots.create(
            volume_id,
            name='temporary_snapshot_of_{0}'.format(volume_id),
            force=True
        )

        snapshot_id = snapshot.id
        is_success = utils.status_poll(
            partial(get_snapshot_status, cinder_client, snapshot_id),
            interval=self._interval,
            success_statuses={'available', },
            failure_statuses={'error', 'error_deleting', 'deleting',
                              'not-found'},
            ignore_statuses={'creating', },
        )
        if is_success is not True:
            try:
                snapshot = cinder_client.volume_snapshots.get(snapshot_id)
            except Exception:
                reason = 'Unable to find volume snapshot.'
            else:
                reason = 'The status of snapshot is %s' % snapshot.status
            raise exception.CreateResourceFailed(
                name="Volume Glance Backup",
                reason=reason,
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE
            )
        LOG.info("Create snapshot of volume({0}) success, "
                 "snapshot_id({1})".format(volume_id, snapshot_id))
        return snapshot_id

    def _create_temporary_volume(self, cinder_client, snapshot_id):
        LOG.info("Start creating volume from snapshot({0}) success"
                 "".format(snapshot_id))
        snapshot = cinder_client.volume_snapshots.get(snapshot_id)
        volume = cinder_client.volumes.create(
            size=snapshot.size,
            snapshot_id=snapshot_id,
            name='temporary_volume_of_{0}'.format(snapshot_id)
        )
        is_success = utils.status_poll(
            partial(get_volume_status, cinder_client, volume.id),
            interval=self._interval,
            success_statuses=VOLUME_SUCCESS_STATUSES,
            failure_statuses=VOLUME_FAILURE_STATUSES,
            ignore_statuses=VOLUME_IGNORE_STATUSES,
        )
        volume = cinder_client.volumes.get(volume.id)
        if is_success is not True:
            LOG.error('The status of temporary volume is invalid. status:%s',
                      volume.status)
            reason = 'Invalid status: %s of temporary volume.' % volume.status
            raise exception.CreateResourceFailed(
                name="Volume Glance Backup",
                reason=reason,
                resource_id=volume.id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )
        LOG.info("Create volume from snapshot({0}) success, "
                 "volume({1})".format(snapshot_id, volume.id))
        return volume

    def _create_temporary_image(self, cinder_client, glance_client,
                                temporary_volume):
        LOG.info("Start creating image from volume({0})."
                 "".format(temporary_volume.id))
        image = cinder_client.volumes.upload_to_image(
            volume=temporary_volume,
            force=True,
            image_name='temporary_image_of_{0}'.format(temporary_volume.id),
            container_format="bare",
            disk_format="raw",
            visibility="private",
            protected=False
        )
        image_id = image[1]['os-volume_upload_image']['image_id']
        is_success = utils.status_poll(
            partial(get_image_status, glance_client, image_id),
            interval=self._interval, success_statuses={'active'},
            ignore_statuses={'queued', 'saving'},
            failure_statuses={'killed', 'deleted', 'pending_delete',
                              'deactivated', 'NotFound'}
        )
        image_info = glance_client.images.get(image_id)
        if is_success is not True:
            LOG.error("The status of image (id: %s) is invalid.",
                      image_id)
            reason = "Invalid status: %s of temporary image." % \
                     image_info.status
            raise exception.CreateResourceFailed(
                name="Volume Glance Backup",
                reason=reason,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)
        LOG.info("Create image({0}) from volume({1}) "
                 "success.".format(image_id, temporary_volume.id))
        return image_id

    def _backup_temporary_image(self, glance_client, image_id, bank_section):
        try:
            chunks_num = utils.backup_image_to_bank(
                glance_client,
                image_id,
                bank_section,
                self._image_object_size
            )
            image_info = glance_client.images.get(image_id)
            image_resource_definition = {
                'chunks_num': chunks_num,
                'image_metadata': {
                    'checksum': image_info.checksum,
                    'disk_format': image_info.disk_format,
                    "container_format": image_info.container_format
                }
            }
            return image_resource_definition
        except Exception as err:
            LOG.exception('Protecting temporary image (id: %s) to bank '
                          'failed.', image_id)
            raise exception.CreateResourceFailed(
                name="Volume Glance Backup",
                reason=err,
                resource_id=image_id,
                resource_type=constants.IMAGE_RESOURCE_TYPE)

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(volume_id)
        cinder_client = ClientFactory.create_client('cinder', context)
        glance_client = ClientFactory.create_client('glance', context)
        LOG.info('creating volume backup by glance, volume_id: %s', volume_id)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        resource_metadata = {
            'volume_id': volume_id,
        }
        is_success = utils.status_poll(
            partial(get_volume_status, cinder_client, volume_id),
            interval=self._interval,
            success_statuses=VOLUME_SUCCESS_STATUSES,
            failure_statuses=VOLUME_FAILURE_STATUSES,
            ignore_statuses=VOLUME_IGNORE_STATUSES,
        )
        if not is_success:
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Volume Glance Backup",
                reason='Volume is in erroneous state',
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

        volume_info = cinder_client.volumes.get(volume_id)
        resource_metadata['volume_size'] = volume_info.size
        snapshot_id = None
        temporary_volume = None
        temporary_image_id = None

        try:
            snapshot_id = self._create_snapshot(cinder_client, volume_id)
            temporary_volume = self._create_temporary_volume(
                cinder_client, snapshot_id)
            temporary_image_id = self._create_temporary_image(
                cinder_client, glance_client, temporary_volume)
            image_resource_metadata = \
                self._backup_temporary_image(glance_client, temporary_image_id,
                                             bank_section)
            metadata = dict(resource_metadata, **image_resource_metadata)
            bank_section.update_object('metadata', metadata)
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info('Backed up volume '
                     '(volume_id: %(volume_id)s '
                     'snapshot_id: %(snapshot_id)s '
                     'temporary_volume_id: %(temporary_volume_id)s) '
                     'temporary_image_id: %(temporary_image_id)s '
                     'successfully', {
                         'volume_id': volume_id,
                         'snapshot_id': snapshot_id,
                         'temporary_volume_id': temporary_volume.id,
                         'temporary_image_id': temporary_image_id
                     })
        finally:
            if snapshot_id:
                try:
                    cinder_client.volume_snapshots.delete(snapshot_id)
                except Exception as e:
                    LOG.warning('Failed deleting snapshot: %(snapshot_id)s. '
                                'Reason: %(reason)s',
                                {'snapshot_id': self.snapshot_id, 'reason': e})

            if temporary_volume:
                try:
                    cinder_client.volumes.delete(temporary_volume.id)
                except Exception as e:
                    LOG.warning('Failed deleting temporary volume: '
                                '%(temporary_volume_id)s. '
                                'Reason: %(reason)s', {
                                    'temporary_volume_id': temporary_volume.id,
                                    'reason': e
                                })
            if temporary_image_id:
                try:
                    glance_client.images.delete(temporary_image_id)
                except Exception as e:
                    LOG.warning('Failed deleting temporary image: '
                                '%(temporary_image_id)s. '
                                'Reason: %(reason)s', {
                                    'temporary_image_id': temporary_image_id,
                                    'reason': e})


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def _create_volume_from_image(self, cinder_client, temporary_image,
                                  restore_name, original_vol_id, volume_size,
                                  description):
        volume = cinder_client.volumes.create(
            size=volume_size,
            imageRef=temporary_image.id,
            name=restore_name,
            description=description
        )
        is_success = utils.status_poll(
            partial(get_volume_status, cinder_client, volume.id),
            interval=self._interval,
            success_statuses=VOLUME_SUCCESS_STATUSES,
            failure_statuses=VOLUME_FAILURE_STATUSES,
            ignore_statuses=VOLUME_IGNORE_STATUSES
        )
        if not is_success:
            LOG.error("Restore volume glance backup failed, so delete "
                      "the temporary volume: volume_id: %s.", original_vol_id)
            cinder_client.volumes.delete(volume.id)
            raise exception.CreateResourceFailed(
                name="Volume Glance Backup",
                reason='Restored Volume is in erroneous state',
                resource_id=volume.id,
                resource_type=constants.VOLUME_RESOURCE_TYPE,
            )

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_volume_id = resource.id
        restore_name = parameters.get('restore_name',
                                      '%s@%s' % (checkpoint.id,
                                                 original_volume_id))
        restore_description = parameters.get('restore_description', None)
        bank_section = checkpoint.get_resource_bank_section(original_volume_id)
        cinder_client = ClientFactory.create_client('cinder', context)
        glance_client = ClientFactory.create_client('glance', context)
        resource_metadata = bank_section.get_object('metadata')
        volume_size = int(resource_metadata['volume_size'])
        temporary_image = None
        try:
            temporary_image = self._create_temporary_image(
                bank_section, glance_client, original_volume_id
            )
            self._create_volume_from_image(cinder_client, temporary_image,
                                           restore_name, original_volume_id,
                                           volume_size, restore_description)
        finally:
            if temporary_image:
                try:
                    glance_client.images.delete(temporary_image.id)
                except Exception as e:
                    LOG.warning('Failed deleting temporary image: '
                                '%(temporary_image_id)s. '
                                'Reason: %(reason)s', {
                                    'temporary_image_id': temporary_image.id,
                                    'reason': e
                                })
        LOG.info("Finish restoring volume backup, volume_id: %s.",
                 original_volume_id)

    def _create_temporary_image(self, bank_section, glance_client,
                                original_volume_id):
        image_info = None
        try:
            image_info = utils.restore_image_from_bank(
                glance_client, bank_section,
                'temporary_image_of_{0}'.format(original_volume_id))

            if image_info.status != "active":
                is_success = utils.status_poll(
                    partial(get_image_status, glance_client, image_info.id),
                    interval=self._interval, success_statuses={'active'},
                    ignore_statuses={'queued', 'saving'},
                    failure_statuses={'killed', 'deleted', 'pending_delete',
                                      'deactivated', 'not-found'}
                )
                if is_success is not True:
                    LOG.error('The status of image is invalid. status:%s',
                              image_info.status)
                    raise exception.RestoreResourceFailed(
                        name="Volume Glance Backup",
                        reason="Create temporary image failed",
                        resource_id=original_volume_id,
                        resource_type=constants.VOLUME_RESOURCE_TYPE)
            return image_info
        except Exception as e:
            LOG.error("Create temporary image of volume failed, "
                      "volume_id: %s.", original_volume_id)
            LOG.exception(e)
            if image_info is not None and hasattr(image_info, 'id'):
                LOG.info("Delete the failed image, image_id: %s.",
                         image_info.id)
                glance_client.images.delete(image_info.id)
            raise exception.RestoreResourceFailed(
                name="Volume Glance Backup",
                reason=e, resource_id=original_volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE)


class VerifyOperation(protection_plugin.Operation):
    def __init__(self):
        super(VerifyOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(
            original_volume_id)
        LOG.info('Verifying the volume backup, volume id: %s',
                 original_volume_id)

        update_method = partial(
            utils.update_resource_verify_result,
            kwargs.get('verify'), resource.type, original_volume_id)

        backup_status = bank_section.get_object("status")

        if backup_status == constants.RESOURCE_STATUS_AVAILABLE:
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = ('The status of volume backup status is %s.'
                      % backup_status)
            update_method(backup_status, reason)
            raise exception.VerifyResourceFailed(
                name="Volume backup",
                reason=reason,
                resource_id=original_volume_id,
                resource_type=resource.type)


class DeleteOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        volume_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(volume_id)

        LOG.info("Deleting volume backup, volume_id: %s.", volume_id)
        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_DELETING)
            objects = bank_section.list_objects()
            for obj in objects:
                if obj == "status":
                    continue
                bank_section.delete_object(obj)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_DELETED)
        except Exception as err:
            LOG.error("delete volume backup failed, volume_id: %s.", volume_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Volume Glance Backup",
                reason=err,
                resource_id=volume_id,
                resource_type=constants.VOLUME_RESOURCE_TYPE)


class VolumeGlanceProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.VOLUME_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(VolumeGlanceProtectionPlugin, self).__init__(config)
        self._config.register_opts(volume_glance_opts,
                                   'volume_glance_plugin')
        self._plugin_config = self._config.volume_glance_plugin
        self._poll_interval = self._plugin_config.poll_interval
        self._backup_from_snapshot = self._plugin_config.backup_from_snapshot
        self._image_object_size = self._plugin_config.backup_image_object_size

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
    def get_verify_schema(cls, resource_type):
        return volume_schemas.VERIFY_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._poll_interval,
                                self._backup_from_snapshot,
                                self._image_object_size)

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_delete_operation(self, resource):
        return DeleteOperation()

    def get_verify_operation(self, resource):
        return VerifyOperation()
