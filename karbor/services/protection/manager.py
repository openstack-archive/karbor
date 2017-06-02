# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Protection Service
"""

from datetime import datetime
from eventlet import greenpool
from eventlet import greenthread
import six

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

from oslo_utils import uuidutils

from karbor.common import constants
from karbor import exception
from karbor.i18n import _
from karbor import manager
from karbor.resource import Resource
from karbor.services.protection.flows import worker as flow_manager
from karbor.services.protection.protectable_registry import ProtectableRegistry
from karbor import utils

LOG = logging.getLogger(__name__)

protection_manager_opts = [
    cfg.StrOpt('provider_registry',
               default='karbor.services.protection.provider.ProviderRegistry',
               help='the provider registry'),
    cfg.IntOpt('max_concurrent_operations',
               default=0,
               help='number of maximum concurrent operation (protect, restore,'
                    ' delete) flows. 0 means no hard limit'
               )
]

CONF = cfg.CONF
CONF.register_opts(protection_manager_opts)

PROVIDER_NAMESPACE = 'karbor.provider'


class ProtectionManager(manager.Manager):
    """karbor Protection Manager."""

    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, service_name=None,
                 *args, **kwargs):
        super(ProtectionManager, self).__init__(*args, **kwargs)
        provider_reg = CONF.provider_registry
        self.provider_registry = utils.load_plugin(PROVIDER_NAMESPACE,
                                                   provider_reg)
        self.protectable_registry = ProtectableRegistry()
        self.protectable_registry.load_plugins()
        self.worker = flow_manager.Worker()
        self._greenpool = None
        self._greenpool_size = CONF.max_concurrent_operations
        if self._greenpool_size != 0:
            self._greenpool = greenpool.GreenPool(self._greenpool_size)

    def _spawn(self, func, *args, **kwargs):
        if self._greenpool is not None:
            return self._greenpool.spawn_n(func, *args, **kwargs)
        else:
            return greenthread.spawn_n(func, *args, **kwargs)

    def init_host(self, **kwargs):
        """Handle initialization if this is a standalone service"""
        # TODO(wangliuan)
        LOG.info("Starting protection service")

    @messaging.expected_exceptions(exception.InvalidPlan,
                                   exception.ProviderNotFound,
                                   exception.FlowError)
    def protect(self, context, plan, checkpoint_properties=None):
        """create protection for the given plan

        :param plan: Define that protection plan should be done
        """

        LOG.info("Starting protection service:protect action")
        LOG.debug("protecting: %s checkpoint_properties:%s",
                  plan, checkpoint_properties)

        if not plan:
            raise exception.InvalidPlan(
                reason=_('the protection plan is None'))
        provider_id = plan.get('provider_id', None)
        plan_id = plan.get('id', None)
        provider = self.provider_registry.show_provider(provider_id)
        checkpoint_collection = provider.get_checkpoint_collection()
        try:
            checkpoint = checkpoint_collection.create(plan,
                                                      checkpoint_properties)
        except Exception as e:
            LOG.exception("Failed to create checkpoint, plan: %s", plan_id)
            exc = exception.FlowError(flow="protect",
                                      error="Error creating checkpoint")
            six.raise_from(exc, e)
        try:
            flow = self.worker.get_flow(
                context=context,
                protectable_registry=self.protectable_registry,
                operation_type=constants.OPERATION_PROTECT,
                plan=plan,
                provider=provider,
                checkpoint=checkpoint)
        except Exception as e:
            LOG.exception("Failed to create protection flow, plan: %s",
                          plan_id)
            raise exception.FlowError(
                flow="protect",
                error=e.msg if hasattr(e, 'msg') else 'Internal error')
        self._spawn(self.worker.run_flow, flow)
        return checkpoint.id

    @messaging.expected_exceptions(exception.ProviderNotFound,
                                   exception.CheckpointNotFound,
                                   exception.CheckpointNotAvailable,
                                   exception.FlowError,
                                   exception.InvalidInput)
    def restore(self, context, restore, restore_auth):
        LOG.info("Starting restore service:restore action")

        checkpoint_id = restore["checkpoint_id"]
        provider_id = restore["provider_id"]
        provider = self.provider_registry.show_provider(provider_id)
        if not provider:
            raise exception.ProviderNotFound(provider_id=provider_id)

        self.validate_restore_parameters(restore, provider)

        checkpoint_collection = provider.get_checkpoint_collection()
        checkpoint = checkpoint_collection.get(checkpoint_id)

        if checkpoint.status != constants.CHECKPOINT_STATUS_AVAILABLE:
            raise exception.CheckpointNotAvailable(
                checkpoint_id=checkpoint_id)

        try:
            flow = self.worker.get_flow(
                context=context,
                operation_type=constants.OPERATION_RESTORE,
                checkpoint=checkpoint,
                provider=provider,
                restore=restore,
                restore_auth=restore_auth)
        except Exception:
            LOG.exception("Failed to create restore flow checkpoint: %s",
                          checkpoint_id)
            raise exception.FlowError(
                flow="restore",
                error=_("Failed to create flow"))
        self._spawn(self.worker.run_flow, flow)

    def validate_restore_parameters(self, restore, provider):
        parameters = restore["parameters"]
        if not parameters:
            return
        restore_schema = provider.extended_info_schema.get(
            "restore_schema", None)
        if restore_schema is None:
            msg = _("The restore schema of plugin must be provided.")
            raise exception.InvalidInput(reason=msg)
        for resource_key, parameter_value in parameters.items():
            if "#" in resource_key:
                resource_type, resource_id = resource_key.split("#")
                if not uuidutils.is_uuid_like(resource_id):
                    msg = _("The resource_id must be a uuid.")
                    raise exception.InvalidInput(reason=msg)
            else:
                resource_type = resource_key
            if (resource_type not in constants.RESOURCE_TYPES) or (
                    resource_type not in restore_schema):
                msg = _("The key of restore parameters is invalid.")
                raise exception.InvalidInput(reason=msg)
            properties = restore_schema[resource_type]["properties"]
            if not set(parameter_value.keys()).issubset(
                    set(properties.keys())):
                msg = _("The restore property of restore parameters "
                        "is invalid.")
                raise exception.InvalidInput(reason=msg)

    def delete(self, context, provider_id, checkpoint_id):
        LOG.info("Starting protection service:delete action")
        LOG.debug('provider_id :%s checkpoint_id:%s', provider_id,
                  checkpoint_id)
        provider = self.provider_registry.show_provider(provider_id)
        try:
            checkpoint_collection = provider.get_checkpoint_collection()
            checkpoint = checkpoint_collection.get(checkpoint_id)
        except Exception:
            LOG.error("get checkpoint failed, checkpoint_id:%s",
                      checkpoint_id)
            raise exception.InvalidInput(
                reason=_("Invalid checkpoint_id or provider_id"))

        if checkpoint.status not in [
            constants.CHECKPOINT_STATUS_AVAILABLE,
            constants.CHECKPOINT_STATUS_ERROR,
        ]:
            raise exception.CheckpointNotBeDeleted(
                checkpoint_id=checkpoint_id)
        checkpoint.status = constants.CHECKPOINT_STATUS_DELETING
        checkpoint.commit()

        try:
            flow = self.worker.get_flow(
                context=context,
                operation_type=constants.OPERATION_DELETE,
                checkpoint=checkpoint,
                provider=provider)
        except Exception:
            LOG.exception("Failed to create delete checkpoint flow,"
                          "checkpoint:%s.", checkpoint_id)
            raise exception.KarborException(_(
                "Failed to create delete checkpoint flow."
            ))
        self._spawn(self.worker.run_flow, flow)

    def start(self, plan):
        # TODO(wangliuan)
        pass

    def suspend(self, plan):
        # TODO(wangliuan)
        pass

    @messaging.expected_exceptions(exception.ProviderNotFound,
                                   exception.CheckpointNotFound)
    def list_checkpoints(self, context, provider_id, marker=None, limit=None,
                         sort_keys=None, sort_dirs=None, filters=None):
        LOG.info("Starting list checkpoints. provider_id:%s", provider_id)
        plan_id = filters.get("plan_id", None)
        start_date = None
        end_date = None
        if filters.get("start_date", None):
            start_date = datetime.strptime(
                filters.get("start_date"), "%Y-%m-%d")
        if filters.get("end_date", None):
            end_date = datetime.strptime(
                filters.get("end_date"), "%Y-%m-%d")
        sort_dir = None if sort_dirs is None else sort_dirs[0]
        provider = self.provider_registry.show_provider(provider_id)
        checkpoint_ids = provider.list_checkpoints(
            provider_id, limit=limit, marker=marker, plan_id=plan_id,
            start_date=start_date, end_date=end_date, sort_dir=sort_dir)
        checkpoints = []
        for checkpoint_id in checkpoint_ids:
            checkpoint = provider.get_checkpoint(checkpoint_id)
            checkpoints.append(checkpoint.to_dict())
        return checkpoints

    @messaging.expected_exceptions(exception.ProviderNotFound,
                                   exception.CheckpointNotFound)
    def show_checkpoint(self, context, provider_id, checkpoint_id):
        provider = self.provider_registry.show_provider(provider_id)

        checkpoint = provider.get_checkpoint(checkpoint_id)
        return checkpoint.to_dict()

    def list_protectable_types(self, context):
        LOG.info("Start to list protectable types.")
        return self.protectable_registry.list_resource_types()

    @messaging.expected_exceptions(exception.ProtectableTypeNotFound)
    def show_protectable_type(self, context, protectable_type):
        LOG.info("Start to show protectable type %s", protectable_type)

        plugin = self.protectable_registry.get_protectable_resource_plugin(
            protectable_type)
        if not plugin:
            raise exception.ProtectableTypeNotFound(
                protectable_type=protectable_type)

        dependents = []
        for t in self.protectable_registry.list_resource_types():
            if t == protectable_type:
                continue

            p = self.protectable_registry.get_protectable_resource_plugin(t)
            if p and protectable_type in p.get_parent_resource_types():
                dependents.append(t)

        return {
            'name': plugin.get_resource_type(),
            "dependent_types": dependents
        }

    @messaging.expected_exceptions(exception.ListProtectableResourceFailed)
    def list_protectable_instances(self, context,
                                   protectable_type=None,
                                   marker=None,
                                   limit=None,
                                   sort_keys=None,
                                   sort_dirs=None,
                                   filters=None,
                                   parameters=None):

        LOG.info("Start to list protectable instances of type: %s",
                 protectable_type)

        try:
            resource_instances = self.protectable_registry.list_resources(
                context, protectable_type, parameters)
        except exception.ListProtectableResourceFailed as err:
            LOG.error("List resources of type %(type)s failed: %(err)s",
                      {'type': protectable_type, 'err': six.text_type(err)})
            raise

        result = []
        for resource in resource_instances:
            result.append(dict(id=resource.id, name=resource.name,
                               extra_info=resource.extra_info))

        return result

    @messaging.expected_exceptions(exception.ListProtectableResourceFailed)
    def show_protectable_instance(self, context, protectable_type,
                                  protectable_id, parameters=None):
        LOG.info("Start to show protectable instance of type: %s",
                 protectable_type)

        registry = self.protectable_registry
        try:
            resource_instance = registry.show_resource(
                context,
                protectable_type,
                protectable_id,
                parameters=parameters
            )
        except exception.ListProtectableResourceFailed as err:
            LOG.error("Show resources of type %(type)s id %(id)s "
                      "failed: %(err)s",
                      {'type': protectable_type,
                       'id': protectable_id,
                       'err': six.text_type(err)})
            raise

        return resource_instance.to_dict()

    @messaging.expected_exceptions(exception.ListProtectableResourceFailed)
    def list_protectable_dependents(self, context,
                                    protectable_id,
                                    protectable_type):
        LOG.info("Start to list dependents of resource (type:%(type)s, "
                 "id:%(id)s)",
                 {'type': protectable_type,
                  'id': protectable_id})

        parent_resource = Resource(type=protectable_type, id=protectable_id,
                                   name="")

        registry = self.protectable_registry
        try:
            dependent_resources = registry.fetch_dependent_resources(
                context, parent_resource)
        except exception.ListProtectableResourceFailed as err:
            LOG.error("List dependent resources of (%(res)s) failed: %(err)s",
                      {'res': parent_resource,
                       'err': six.text_type(err)})
            raise

        return [resource.to_dict() for resource in dependent_resources]

    def list_providers(self, context, marker=None, limit=None,
                       sort_keys=None, sort_dirs=None, filters=None):
        return self.provider_registry.list_providers(marker=marker,
                                                     limit=limit,
                                                     sort_keys=sort_keys,
                                                     sort_dirs=sort_dirs,
                                                     filters=filters)

    @messaging.expected_exceptions(exception.ProviderNotFound)
    def show_provider(self, context, provider_id):
        provider = self.provider_registry.show_provider(provider_id)
        response = {'id': provider.id,
                    'name': provider.name,
                    'description': provider.description,
                    'extended_info_schema': provider.extended_info_schema,
                    }
        return response
