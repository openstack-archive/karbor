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
from karbor.services.protection.protection_plugins.share \
    import share_snapshot_plugin_schemas as share_schemas
from karbor.services.protection.protection_plugins import utils
from manilaclient import exceptions as manila_exc
from oslo_config import cfg
from oslo_log import log as logging

LOG = logging.getLogger(__name__)

manila_snapshot_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Manila share status.'
    )
]

SHARE_FAILURE_STATUSES = {'error', 'error_deleting', 'deleting',
                          'not-found', 'extending_error',
                          'shrinking_error', 'reverting_error'}

SHARE_IGNORE_STATUSES = {'creating', 'reverting', 'extending',
                         'shrinking'}


def get_snapshot_status(manila_client, snapshot_id):
    return get_resource_status(manila_client.share_snapshots, snapshot_id,
                               'snapshot')


def get_share_status(manila_client, share_id):
    return get_resource_status(manila_client.shares, share_id, 'share')


def get_resource_status(resource_manager, resource_id, resource_type):
    LOG.debug('Polling %(resource_type)s (id: %(resource_id)s)',
              {'resource_type': resource_type, 'resource_id': resource_id})
    try:
        resource = resource_manager.get(resource_id)
        status = resource.status
    except manila_exc.NotFound:
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

    def _create_snapshot(self, manila_client, share_id, snapshot_name,
                         description, force):
        snapshot = manila_client.share_snapshots.create(
            share=share_id,
            name=snapshot_name,
            description=description,
            force=force
        )

        snapshot_id = snapshot.id
        is_success = utils.status_poll(
            partial(get_snapshot_status, manila_client, snapshot_id),
            interval=self._interval,
            success_statuses={'available'},
            failure_statuses={'error'},
            ignore_statuses={'creating'},
            ignore_unexpected=True
        )

        if not is_success:
            try:
                snapshot = manila_client.share_snapshots.get(snapshot_id)
            except Exception:
                reason = 'Unable to find snapshot.'
            else:
                reason = 'The status of snapshot is %s' % snapshot.status
            raise exception.CreateResourceFailed(
                name="Share Snapshot",
                reason=reason, resource_id=share_id,
                resource_type=constants.SHARE_RESOURCE_TYPE)

        return snapshot_id

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        share_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(share_id)
        manila_client = ClientFactory.create_client('manila', context)
        LOG.info('creating share snapshot, share_id: %s', share_id)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)
        share_info = manila_client.shares.get(share_id)
        if share_info.status != "available":
            is_success = utils.status_poll(
                partial(get_share_status, manila_client, share_id),
                interval=self._interval, success_statuses={'available'},
                failure_statuses=SHARE_FAILURE_STATUSES,
                ignore_statuses=SHARE_IGNORE_STATUSES,
            )
            if not is_success:
                bank_section.update_object('status',
                                           constants.RESOURCE_STATUS_ERROR)
                raise exception.CreateResourceFailed(
                    name="Share Snapshot",
                    reason='Share is in a error status.',
                    resource_id=share_id,
                    resource_type=constants.SHARE_RESOURCE_TYPE,
                )
        resource_metadata = {
            'share_id': share_id,
            'size': share_info.size,
            'share_proto': share_info.share_proto,
            'share_type': share_info.share_type,
            'share_network_id': share_info.share_network_id
        }
        snapshot_name = parameters.get('snapshot_name', None)
        description = parameters.get('description', None)
        force = parameters.get('force', False)
        try:
            snapshot_id = self._create_snapshot(manila_client, share_id,
                                                snapshot_name,
                                                description, force)
        except exception.CreateResourceFailed as e:
            LOG.error('Error creating snapshot (share_id: %(share_id)s '
                      ': %(reason)s', {'share_id': share_id, 'reason': e})
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise

        resource_metadata['snapshot_id'] = snapshot_id

        bank_section.update_object('metadata', resource_metadata)
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_AVAILABLE)
        LOG.info('Snapshot share (share_id: %(share_id)s snapshot_id: '
                 '%(snapshot_id)s ) successfully',
                 {'share_id': share_id, 'snapshot_id': snapshot_id})


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_share_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(original_share_id)
        manila_client = ClientFactory.create_client('manila', context)
        resource_metadata = bank_section.get_object('metadata')
        restore_name = parameters.get('restore_name',
                                      '%s@%s' % (checkpoint.id,
                                                 original_share_id))
        restore_description = parameters.get('restore_description', None)
        snapshot_id = resource_metadata['snapshot_id']
        share_proto = resource_metadata['share_proto']
        size = resource_metadata['size']
        share_type = resource_metadata['share_type']
        share_network_id = resource_metadata['share_network_id']
        restore = kwargs.get('restore')
        LOG.info("Restoring a share from snapshot, "
                 "original_share_id: %s.", original_share_id)
        try:
            share = manila_client.shares.create(
                share_proto, size, snapshot_id=snapshot_id,
                name=restore_name, description=restore_description,
                share_network=share_network_id, share_type=share_type)
            is_success = utils.status_poll(
                partial(get_share_status, manila_client, share.id),
                interval=self._interval, success_statuses={'available'},
                failure_statuses=SHARE_FAILURE_STATUSES,
                ignore_statuses=SHARE_IGNORE_STATUSES
            )
            if is_success is not True:
                LOG.error('The status of share is invalid. status:%s',
                          share.status)
                restore.update_resource_status(
                    constants.SHARE_RESOURCE_TYPE,
                    share.id, share.status, "Invalid status.")
                restore.save()
                raise exception.RestoreResourceFailed(
                    name="Share Snapshot",
                    reason="Invalid status.",
                    resource_id=original_share_id,
                    resource_type=constants.SHARE_RESOURCE_TYPE)
            restore.update_resource_status(constants.SHARE_RESOURCE_TYPE,
                                           share.id, share.status)
            restore.save()
        except Exception as e:
            LOG.error("Restore share from snapshot failed, share_id: %s.",
                      original_share_id)
            raise exception.RestoreResourceFailed(
                name="Share Snapshot",
                reason=e, resource_id=original_share_id,
                resource_type=constants.SHARE_RESOURCE_TYPE)
        LOG.info("Finish restoring a share from snapshot, share_id: %s.",
                 original_share_id)


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
            manila_client = ClientFactory.create_client('manila', context)
            try:
                snapshot = manila_client.share_snapshots.get(snapshot_id)
                manila_client.share_snapshots.delete(snapshot)
            except manila_exc.NotFound:
                LOG.info('Snapshot id: %s not found. Assuming deleted',
                         snapshot_id)
            is_success = utils.status_poll(
                partial(get_snapshot_status, manila_client, snapshot_id),
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
            LOG.error('Delete share snapshot failed, snapshot_id: %s',
                      snapshot_id)
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Share Snapshot",
                reason=six.text_type(e),
                resource_id=resource_id,
                resource_type=constants.SHARE_RESOURCE_TYPE
            )


class ManilaSnapshotProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.SHARE_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(ManilaSnapshotProtectionPlugin, self).__init__(config)
        self._config.register_opts(manila_snapshot_opts,
                                   'manila_snapshot_plugin')
        self._plugin_config = self._config.manila_snapshot_plugin
        self._poll_interval = self._plugin_config.poll_interval

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resources_type):
        return share_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resources_type):
        return share_schemas.RESTORE_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resources_type):
        return share_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._poll_interval)

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_delete_operation(self, resource):
        return DeleteOperation(self._poll_interval)
