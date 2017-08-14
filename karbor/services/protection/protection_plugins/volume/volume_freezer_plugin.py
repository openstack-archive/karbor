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

import random

from functools import partial
from oslo_config import cfg
from oslo_log import log as logging

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins import utils
from karbor.services.protection.protection_plugins.volume import \
    volume_freezer_plugin_schemas

LOG = logging.getLogger(__name__)

freezer_backup_opts = [
    cfg.IntOpt(
        'poll_interval', default=20,
        help='Poll interval for Freezer Backup Resource status.'
    ),
    cfg.StrOpt(
        'scheduler_client_id', default=None,
        help='The freezer scheduler client id to schedule the jobs'
    ),
    cfg.StrOpt(
        'container', default='karbor',
        help='The container for Freezer backup storage.'
    ),
    cfg.StrOpt(
        'storage', default='swift',
        help='The storage type for Freezer backup storage.'
    ),
    cfg.StrOpt(
        'ssh_key',
        help='The ssh key for Freezer ssh driver.'
    ),
    cfg.StrOpt(
        'ssh_username',
        help='The ssh user name for Freezer ssh driver.'
    ),
    cfg.StrOpt(
        'ssh_host',
        help='The ssh host for Freezer ssh driver.'
    ),
    cfg.StrOpt(
        'ssh_port',
        help='The ssh port for Freezer ssh driver.'
    ),
    cfg.StrOpt(
        'endpoint',
        help='The storage endpoint for Freezer S3 driver.'
    ),
    cfg.StrOpt(
        'access_key',
        help='The storage access key for Freezer S3 driver.'
    ),
    cfg.StrOpt(
        'secret_key',
        help='The storage secret key for Freezer S3 driver.'
    )
]


def get_job_status(freezer_job_operation, job_id):
    LOG.debug('Polling freezer job status, job_id: {0}'.format(job_id))
    job_status = freezer_job_operation.get_status(job_id)
    LOG.debug('Polled freezer job status, job_id: {0}, job_status: {1}'.format(
        job_id, job_status
    ))
    return job_status


class FreezerStorage(object):
    def __init__(self, storage_type, storage_path, **kwargs):
        self.storage_type = storage_type
        self.storage_path = storage_path
        self.config = kwargs

    def get_storage(self):

        storage = {
            'storage': self.storage_type,
            'container': self.storage_path
        }

        if self.storage_type == 's3':
            storage['endpoint'] = self.config.get('endpoint', None)
            storage['access_key'] = self.config.get('access_key', None)
            storage['secret_key'] = self.config.get('secret_key', None)

        if self.storage_type == 'ssh':
            storage['ssh_key'] = self.config.get('ssh_key', None)
            storage['ssh_port'] = self.config.get('ssh_port', None)
            storage['ssh_username'] = self.config.get('ssh_username', None)
            storage['ssh_host'] = self.config.get('ssh_host', None)

        return storage


class FreezerTask(object):
    def __init__(self, context):
        self.context = context
        self.client = ClientFactory.create_client('freezer', self.context)

    def _client(self):
        return self.client

    def get(self, job_id):
        return self._client().jobs.get(job_id)

    def get_status(self, job_id):
        return self._client().jobs.get(job_id).get('job_schedule',
                                                   {}).get('result')

    def create(self, backup_name, storage, description, resource,
               action_type, scheduler_client_id):
        return self._build(backup_name, storage, description,
                           resource, action_type, scheduler_client_id)

    def create_delete_job(self, job):
        for job_action in job['job_actions']:
            job_action['freezer_action']['action'] = 'admin'
            job_action['freezer_action']['remove_older_than'] = '-1'
        job_id = self._client().jobs.create(job)
        self._client().jobs.start_job(job_id)
        return job_id, job

    def create_restore_job(self, job):
        for job_action in job['job_actions']:
            job_action['freezer_action']['action'] = 'restore'
        job_id = self._client().jobs.create(job)
        self._client().jobs.start_job(job_id)
        return job_id, job

    def delete(self, job_id):
        actions = self.actions(job_id)
        for action in actions:
            self._client().actions.delete(action.get('action_id'))
        return self._client().jobs.delete(job_id)

    def actions(self, job_id):
        job = self.get(job_id)
        if not job:
            return []
        return job.get('job_actions', [])

    def _build(self, backup_name, storage, description,
               resource, action_type, scheduler_client_id):
        client_id = scheduler_client_id if scheduler_client_id else \
            FreezerSchedulerClient(self._client()).get_random_client_id()
        job = {
            'description': resource.id if not description else description,
            'job_actions': [self._build_action(
                backup_name=backup_name,
                storage=storage,
                resource=resource,
                action_type=action_type,
            )],
            'client_id': client_id
        }

        job_id = self._client().jobs.create(job)
        self._client().jobs.start_job(job_id)
        return job_id, job

    @staticmethod
    def _build_action(backup_name, storage, resource, action_type):
        backup_name = backup_name.replace(' ', '_')
        action = {
            'backup_name': backup_name,
            'action': action_type,
            'mode': 'cinder',
            'cinder_vol_id': resource.id
        }

        action = dict(action, **storage.get_storage())

        if action_type == 'admin':
            action['remove_older_than'] = '-1'

        return {'freezer_action': action}


class FreezerSchedulerClient(object):
    """Freezer scheduler to schedule the jobs.

    All the freezer scheduler clients should be able to schedule jobs
    which resource type is nova instance or cinder volume.
    """

    def __init__(self, freezer_client):
        self.client = freezer_client

    def get_random_client_id(self):
        clients = self.client.clients.list()
        if len(clients) < 1:
            raise Exception('No freezer-scheduler client exist')
        client_index = random.randint(0, len(clients) - 1)
        return [
            c.get('client', {}).get('client_id') for c in clients
        ][client_index]


class ProtectOperation(protection_plugin.Operation):
    def __init__(self, poll_interval, freezer_storage, scheduler_client_id):
        super(ProtectOperation, self).__init__()
        self._poll_interval = poll_interval
        self._scheduler_client_id = scheduler_client_id
        self.freezer_storage = freezer_storage

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)

        LOG.info('Creating freezer protection backup, resource_id: {0}'
                 .format(resource_id))
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_PROTECTING)

        backup_name = parameters.get('backup_name', 'backup{0}'
                                     .format(resource_id))
        description = parameters.get('description', None)
        self.freezer_storage.storage_path = "{0}/{1}".format(
            self.freezer_storage.storage_path, checkpoint.id)
        job_id, job_info = None, None
        freezer_task = FreezerTask(context)
        try:
            job_id, job_info = freezer_task.create(
                backup_name=backup_name,
                storage=self.freezer_storage,
                description=description,
                resource=resource,
                action_type='backup',
                scheduler_client_id=self._scheduler_client_id
            )
            LOG.debug('Creating freezer backup job successful, job_id: {0}'
                      .format(job_id))
            is_success = utils.status_poll(
                partial(get_job_status, freezer_task, job_id),
                interval=self._poll_interval,
                success_statuses={'success'},
                failure_statuses={'fail'},
                ignore_statuses={'aborted', ''},
                ignore_unexpected=True
            )

            if is_success is not True:
                LOG.error("The status of freezer job (id: {0}) is invalid."
                          .format(job_id))
                raise exception.CreateResourceFailed(
                    name="Freezer Backup FreezerTask",
                    reason="The status of freezer job is invalid.",
                    resource_id=resource_id,
                    resource_type=resource.type)

            resource_definition = {
                'job_id': job_id,
                'job_info': job_info
            }

            bank_section.update_object("metadata", resource_definition)

            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_AVAILABLE)

        except exception.CreateResourceFailed as e:
            LOG.error('Error creating backup (resource_id: {0}, reason: {1})'
                      .format(resource_id, e))
            if job_id:
                freezer_task.delete(job_id)
            bank_section.update_object('status',
                                       constants.RESOURCE_STATUS_ERROR)
            raise
        LOG.debug('Finish creating freezer backup resource')
        freezer_task.delete(job_id)


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._poll_interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        LOG.info("Creating freezer protection backup, resource_id: {0}"
                 .format(resource_id))

        resource_metadata = bank_section.get_object('metadata')
        freezer_job_info = resource_metadata.get('job_info', None)
        if not freezer_job_info:
            raise exception.RestoreResourceFailed(
                name='Freezer Backup FreezerTask',
                reason='The content of freezer job is invalid.',
                resource_id=resource_id,
                resource_type=resource.type
            )
        freezer_task = FreezerTask(context)
        job_id, job_info = None, None
        try:
            job_id, job_info = freezer_task.create_restore_job(
                freezer_job_info
            )
            is_success = utils.status_poll(
                partial(get_job_status, freezer_task, job_id),
                interval=self._poll_interval,
                success_statuses={'success'},
                failure_statuses={'fail'},
                ignore_statuses={'aborted', ''},
                ignore_unexpected=True
            )

            if is_success is not True:
                LOG.error("The status of freezer job (id: {0}) is invalid."
                          .format(job_id))
                raise exception.RestoreResourceFailed(
                    name="Freezer Backup FreezerTask",
                    reason="The status of freezer job is invalid.",
                    resource_id=resource_id,
                    resource_type=resource.type
                )

        except Exception as e:
            LOG.error("Restore freezer backup resource failed, resource_type:"
                      "{0}, resource_id: {1}"
                      .format(resource.type, resource.id))
            if job_id:
                freezer_task.delete(job_id)
            raise exception.RestoreResourceFailed(
                name="Freezer Backup FreezerTask",
                reason=e,
                resource_id=resource_id,
                resource_type=resource.type
            )
        LOG.debug('Finish restoring freezer backup resource')
        freezer_task.delete(job_id)


class DeleteOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(DeleteOperation, self).__init__()
        self._poll_interval = poll_interval

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)
        LOG.info("Deleting freezer protection backup, resource_id: {0}"
                 .format(resource_id))

        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_DELETING)
        resource_metadata = bank_section.get_object('metadata')
        freezer_task_info = resource_metadata.get('job_info', None)
        if not freezer_task_info:
            raise exception.DeleteResourceFailed(
                name='Freezer Backup FreezerTask',
                reason='The content of freezer job is invalid.',
                resource_id=resource_id,
                resource_type=resource.type
            )

        freezer_job_operation = FreezerTask(context)
        job_id, job_info = None, None
        try:
            job_id, job_info = freezer_job_operation.create_delete_job(
                freezer_task_info
            )

            is_success = utils.status_poll(
                partial(get_job_status, freezer_job_operation, job_id),
                interval=self._poll_interval,
                success_statuses={'success'},
                failure_statuses={'fail'},
                ignore_statuses={'aborted', ''},
                ignore_unexpected=True
            )

            if is_success is not True:
                LOG.error("The status of freezer job (id: {0}) is invalid."
                          .format(job_id))
                raise exception.CreateResourceFailed(
                    name="Freezer Backup FreezerTask",
                    reason="The status of freezer job is invalid.",
                    resource_id=resource_id,
                    resource_type=resource.type
                )
        except Exception as e:
            LOG.error("Delete freezer backup resource failed, resource_type:"
                      "{0}, resource_id: {1}"
                      .format(resource.type, resource.id))
            if job_id:
                freezer_job_operation.delete(job_id)
            raise exception.DeleteResourceFailed(
                name="Freezer Backup FreezerTask",
                reason=e,
                resource_id=resource_id,
                resource_type=resource.type
            )
        LOG.debug('Finish deleting freezer backup resource')
        bank_section.delete_object('metadata')
        bank_section.update_object('status',
                                   constants.RESOURCE_STATUS_DELETED)
        freezer_job_operation.delete(job_id)


class FreezerProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.VOLUME_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(FreezerProtectionPlugin, self).__init__(config)
        self._config.register_opts(freezer_backup_opts,
                                   'freezer_protection_plugin')
        self._plugin_config = self._config.freezer_protection_plugin
        self._poll_interval = self._plugin_config.poll_interval
        self._scheduler_client_id = self._plugin_config.scheduler_client_id
        self._freezer_storage = FreezerStorage(
            storage_type=self._plugin_config.storage,
            storage_path=self._plugin_config.container,
            endpoint=self._plugin_config.endpoint,
            access_key=self._plugin_config.access_key,
            secret_key=self._plugin_config.secret_key,
            ssh_key=self._plugin_config.ssh_key,
            ssh_port=self._plugin_config.ssh_port,
            ssh_username=self._plugin_config.ssh_username,
            ssh_host=self._plugin_config.ssh_host
        )

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resource_type):
        return volume_freezer_plugin_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resource_type):
        return volume_freezer_plugin_schemas.RESTORE_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        return volume_freezer_plugin_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation(self._poll_interval,
                                self._freezer_storage,
                                self._scheduler_client_id
                                )

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_delete_operation(self, resource):
        return DeleteOperation(self._poll_interval)
