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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import uuidutils

from karbor.common import constants
from karbor import exception
from karbor.services.protection.client_factory import ClientFactory
from karbor.services.protection import protection_plugin
from karbor.services.protection.protection_plugins.pod \
    import pod_plugin_schemas
from karbor.services.protection.protection_plugins import utils


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

pod_backup_opts = [
    cfg.IntOpt(
        'poll_interval', default=15,
        help='Poll interval for Pod backup status'
    ),
]


class ProtectOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        pod_id = resource.id
        pod_name = resource.name
        bank_section = checkpoint.get_resource_bank_section(pod_id)
        k8s_client = ClientFactory.create_client("k8s", context)
        resource_definition = {"resource_id": pod_id}

        LOG.info("Creating pod backup, id: %(pod_id)s) name: "
                 "%(pod_name)s.", {"pod_id": pod_id, "pod_name": pod_name})
        try:
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_PROTECTING)

            # get metadata about pod
            pod_namespace, k8s_pod_name = pod_name.split(":")
            pod = k8s_client.read_namespaced_pod(
                k8s_pod_name, pod_namespace)
            resource_definition["resource_name"] = pod_name
            resource_definition["namespace"] = pod_namespace

            mounted_volumes_list = self._get_mounted_volumes(
                k8s_client, pod, pod_namespace)
            containers_list = self._get_containers(pod)

            # save all pod's metadata
            pod_metadata = {
                'apiVersion': pod.api_version,
                'kind': pod.kind,
                'metadata': {
                    'labels': pod.metadata.labels,
                    'name': pod.metadata.name,
                    'namespace': pod.metadata.namespace,
                },
                'spec': {
                    'containers': containers_list,
                    'volumes': mounted_volumes_list,
                    'restartPolicy': pod.spec.restart_policy
                }
            }
            resource_definition["pod_metadata"] = pod_metadata
            LOG.debug("Creating pod backup, pod_metadata: %s.",
                      pod_metadata)
            bank_section.update_object("metadata", resource_definition)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info("Finish backup pod, pod_id: %s.", pod_id)
        except Exception as err:
            LOG.exception("Create pod backup failed, pod_id: %s.", pod_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.CreateResourceFailed(
                name="Pod Backup",
                reason=err,
                resource_id=pod_id,
                resource_type=constants.POD_RESOURCE_TYPE)

    def _get_mounted_volumes(self, k8s_client, pod, pod_namespace):
        mounted_volumes_list = []
        for volume in pod.spec.volumes:
            volume_pvc = volume.persistent_volume_claim
            volume_cinder = volume.cinder
            volume_pvc_name = volume.name

            if volume_pvc:
                pvc_name = volume_pvc.claim_name
                pvc = k8s_client.read_namespaced_persistent_volume_claim(
                    pvc_name, pod_namespace)
                pv_name = pvc.spec.volume_name
                if pv_name:
                    pv = k8s_client.read_persistent_volume(pv_name)
                    if pv.spec.cinder:
                        pod_cinder_volume = {
                            'name': volume_pvc_name,
                            'cinder': {
                                "volumeID": pv.spec.cinder.volume_id,
                                "fsType": pv.spec.cinder.fs_type,
                                "readOnly": pv.spec.cinder.read_only
                            }
                        }
                        mounted_volumes_list.append(pod_cinder_volume)
            elif volume_cinder:
                pod_cinder_volume = {
                    'name': volume_pvc_name,
                    'cinder': {
                        "volumeID": volume_cinder.volume_id,
                        "fsType": volume_cinder.fs_type,
                        "readOnly": volume_cinder.read_only
                    }
                }
                mounted_volumes_list.append(pod_cinder_volume)
        return mounted_volumes_list

    def _get_containers(self, pod):
        containers_list = []
        for spec_container in pod.spec.containers:
            resources = (spec_container.resources.to_dict()
                         if spec_container.resources else None)
            volume_mounts_list = []
            if spec_container.volume_mounts:
                for spec_volume_mount in spec_container.volume_mounts:
                    if 'serviceaccount' in spec_volume_mount.mount_path:
                        continue
                    volume_mount = {
                        'name': spec_volume_mount.name,
                        'mountPath': spec_volume_mount.mount_path,
                        'readOnly': spec_volume_mount.read_only,
                    }
                    volume_mounts_list.append(volume_mount)
            container = {
                'command': spec_container.command,
                'image': spec_container.image,
                'name': spec_container.name,
                'resources': resources,
                'volumeMounts': volume_mounts_list
            }
            containers_list.append(container)
        return containers_list


class DeleteOperation(protection_plugin.Operation):
    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        resource_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(resource_id)

        LOG.info("Deleting pod backup, pod_id: %s.", resource_id)

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
            LOG.info("Finish delete pod, pod_id: %s.", resource_id)
        except Exception as err:
            LOG.error("Delete backup failed, pod_id: %s.", resource_id)
            bank_section.update_object("status",
                                       constants.RESOURCE_STATUS_ERROR)
            raise exception.DeleteResourceFailed(
                name="Pod Backup",
                reason=err,
                resource_id=resource_id,
                resource_type=constants.POD_RESOURCE_TYPE)


class VerifyOperation(protection_plugin.Operation):
    def __init__(self):
        super(VerifyOperation, self).__init__()

    def on_main(self, checkpoint, resource, context, parameters, **kwargs):
        original_pod_id = resource.id
        bank_section = checkpoint.get_resource_bank_section(
            original_pod_id)
        LOG.info('Verifying the pod backup, pod_id: %s.', original_pod_id)

        update_method = partial(
            utils.update_resource_verify_result,
            kwargs.get('verify'), resource.type, original_pod_id)

        backup_status = bank_section.get_object("status")

        if backup_status == constants.RESOURCE_STATUS_AVAILABLE:
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
        else:
            reason = ('The status of pod backup status is %s.'
                      % backup_status)
            update_method(backup_status, reason)
            raise exception.VerifyResourceFailed(
                name="Pod backup",
                reason=reason,
                resource_id=original_pod_id,
                resource_type=resource.type)


class RestoreOperation(protection_plugin.Operation):
    def __init__(self, poll_interval):
        super(RestoreOperation, self).__init__()
        self._interval = poll_interval

    def on_complete(self, checkpoint, resource, context, parameters, **kwargs):
        original_pod_id = resource.id
        LOG.info("Restoring pod backup, pod_id: %s.", original_pod_id)

        update_method = None
        try:
            resource_definition = checkpoint.get_resource_bank_section(
                original_pod_id).get_object("metadata")

            LOG.debug("Restoring pod backup, metadata: %s.",
                      resource_definition)

            k8s_client = ClientFactory.create_client("k8s", context)
            new_resources = kwargs.get("new_resources")

            # restore pod
            new_pod_name = self._restore_pod_instance(
                k8s_client, new_resources, original_pod_id,
                parameters.get(
                    "restore_name",
                    "karbor-restored-pod-%s" % uuidutils.generate_uuid()),
                resource_definition)

            update_method = partial(utils.update_resource_restore_result,
                                    kwargs.get('restore'), resource.type,
                                    new_pod_name)
            update_method(constants.RESOURCE_STATUS_RESTORING)
            pod_namespace = resource_definition["namespace"]
            self._wait_pod_to_running(k8s_client, new_pod_name,
                                      pod_namespace)

            new_resources[original_pod_id] = new_pod_name
            update_method(constants.RESOURCE_STATUS_AVAILABLE)
            LOG.info("Finish restore pod, pod_id: %s.",
                     original_pod_id)

        except Exception as e:
            if update_method:
                update_method(constants.RESOURCE_STATUS_ERROR, str(e))
            LOG.exception("Restore pod backup failed, pod_id: %s.",
                          original_pod_id)
            raise exception.RestoreResourceFailed(
                name="Pod Backup",
                reason=e,
                resource_id=original_pod_id,
                resource_type=constants.POD_RESOURCE_TYPE
            )

    def _restore_pod_instance(self, k8s_client, new_resources,
                              original_id, restore_name,
                              resource_definition):
        pod_namespace = resource_definition["namespace"]
        pod_metadata = resource_definition["pod_metadata"]
        mounted_volumes_list = pod_metadata['spec'].get("volumes", None)
        if mounted_volumes_list:
            for mounted_volume in mounted_volumes_list:
                cinder_volume = mounted_volume.get("cinder", None)
                if cinder_volume:
                    original_volume_id = cinder_volume["volumeID"]
                    cinder_volume["volumeID"] = new_resources.get(
                        original_volume_id)
        pod_metadata["metadata"]["name"] = restore_name
        pod_manifest = pod_metadata

        LOG.debug("Restoring pod instance, pod_manifest: %s.",
                  pod_manifest)
        try:
            pod = k8s_client.create_namespaced_pod(body=pod_manifest,
                                                   namespace=pod_namespace)
        except Exception as ex:
            LOG.error('Error creating pod (pod_id:%(pod_id)s): '
                      '%(reason)s', {'server_id': original_id, 'reason': ex})
            raise

        return pod.metadata.name

    def _wait_pod_to_running(self, k8s_client, pod_name, pod_namespace):
        def _get_pod_status():
            try:
                pod = k8s_client.read_namespaced_pod(name=pod_name,
                                                     namespace=pod_namespace)
                return pod.status.phase
            except Exception as ex:
                LOG.error('Fetch pod(%(pod_name)s) failed, '
                          'reason: %(reason)s',
                          {'pod_name': pod_name,
                           'reason': ex})
                return 'ERROR'

        is_success = utils.status_poll(
            _get_pod_status,
            interval=self._interval,
            success_statuses={'Running', },
            failure_statuses={'ERROR', 'Failed', 'Unknown'},
            ignore_statuses={'Pending'},
        )
        if not is_success:
            raise Exception('The pod does not run successfully')


class PodProtectionPlugin(protection_plugin.ProtectionPlugin):
    _SUPPORT_RESOURCE_TYPES = [constants.POD_RESOURCE_TYPE]

    def __init__(self, config=None):
        super(PodProtectionPlugin, self).__init__(config)
        self._config.register_opts(pod_backup_opts,
                                   'pod_backup_protection_plugin')
        self._poll_interval = (
            self._config.pod_backup_protection_plugin.poll_interval)

    @classmethod
    def get_supported_resources_types(cls):
        return cls._SUPPORT_RESOURCE_TYPES

    @classmethod
    def get_options_schema(cls, resource_type):
        return pod_plugin_schemas.OPTIONS_SCHEMA

    @classmethod
    def get_restore_schema(cls, resource_type):
        return pod_plugin_schemas.RESTORE_SCHEMA

    @classmethod
    def get_verify_schema(cls, resources_type):
        return pod_plugin_schemas.VERIFY_SCHEMA

    @classmethod
    def get_saved_info_schema(cls, resource_type):
        return pod_plugin_schemas.SAVED_INFO_SCHEMA

    @classmethod
    def get_saved_info(cls, metadata_store, resource):
        pass

    def get_protect_operation(self, resource):
        return ProtectOperation()

    def get_restore_operation(self, resource):
        return RestoreOperation(self._poll_interval)

    def get_verify_operation(self, resource):
        return VerifyOperation()

    def get_delete_operation(self, resource):
        return DeleteOperation()
