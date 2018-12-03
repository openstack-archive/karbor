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

from oslo_service import wsgi as base_wsgi

from karbor.api.openstack import ProjectMapper
from karbor.api.v1 import copies
from karbor.api.v1 import operation_logs
from karbor.api.v1 import plans
from karbor.api.v1 import protectables
from karbor.api.v1 import providers
from karbor.api.v1 import quota_classes
from karbor.api.v1 import quotas
from karbor.api.v1 import restores
from karbor.api.v1 import scheduled_operations
from karbor.api.v1 import services
from karbor.api.v1 import triggers
from karbor.api.v1 import verifications


class APIRouter(base_wsgi.Router):
    @classmethod
    def factory(cls, global_conf, **local_conf):
        return cls(ProjectMapper())

    def __init__(self, mapper):
        plans_resources = plans.create_resource()
        restores_resources = restores.create_resource()
        protectables_resources = protectables.create_resource()
        providers_resources = providers.create_resource()
        trigger_resources = triggers.create_resource()
        scheduled_operation_resources = scheduled_operations.create_resource()
        operation_log_resources = operation_logs.create_resource()
        verification_resources = verifications.create_resource()
        service_resources = services.create_resource()
        quota_resources = quotas.create_resource()
        quota_class_resources = quota_classes.create_resource()
        copy_resources = copies.create_resource()

        mapper.resource("plan", "plans",
                        controller=plans_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("restore", "restores",
                        controller=restores_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("protectable", "protectables",
                        controller=protectables_resources,
                        collection={},
                        member={})
        mapper.connect("protectable",
                       "/{project_id}/protectables/"
                       "{protectable_type}/instances",
                       controller=protectables_resources,
                       action='instances_index',
                       conditions={"method": ['GET']})
        mapper.connect("protectable",
                       "/{project_id}/protectables/"
                       "{protectable_type}/instances/{protectable_id}",
                       controller=protectables_resources,
                       action='instances_show',
                       conditions={"method": ['GET']})
        mapper.resource("provider", "providers",
                        controller=providers_resources,
                        collection={},
                        member={})
        mapper.connect("provider",
                       "/{project_id}/providers/{provider_id}/checkpoints",
                       controller=providers_resources,
                       action='checkpoints_index',
                       conditions={"method": ['GET']})
        mapper.connect("provider",
                       "/{project_id}/providers/{provider_id}/checkpoints",
                       controller=providers_resources,
                       action='checkpoints_create',
                       conditions={"method": ['POST']})
        mapper.connect("provider",
                       "/{project_id}/providers/{provider_id}/checkpoints/"
                       "{checkpoint_id}",
                       controller=providers_resources,
                       action='checkpoints_show',
                       conditions={"method": ['GET']})
        mapper.connect("provider",
                       "/{project_id}/providers/{provider_id}/checkpoints/"
                       "{checkpoint_id}",
                       controller=providers_resources,
                       action='checkpoints_delete',
                       conditions={"method": ['DELETE']})
        mapper.connect("provider",
                       "/{project_id}/providers/{provider_id}/checkpoints/"
                       "{checkpoint_id}",
                       controller=providers_resources,
                       action='checkpoints_update',
                       conditions={'method': ['PUT']})
        mapper.resource("trigger", "triggers",
                        controller=trigger_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("scheduled_operation", "scheduled_operations",
                        controller=scheduled_operation_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("operation_log", "operation_logs",
                        controller=operation_log_resources,
                        collection={},
                        member={})
        mapper.resource("verification", "verifications",
                        controller=verification_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("os-service", "os-services",
                        controller=service_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("quota", "quotas",
                        controller=quota_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.connect("quota",
                       "/{project_id}/quotas/{id}/defaults",
                       controller=quota_resources,
                       action='defaults',
                       conditions={"method": ['GET']})
        mapper.connect("quota",
                       "/{project_id}/quotas/{id}/detail",
                       controller=quota_resources,
                       action='detail',
                       conditions={"method": ['GET']})
        mapper.resource("quota_class", "quota_classes",
                        controller=quota_class_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.connect("copy",
                       "/{project_id}/providers/{provider_id}/checkpoints/"
                       "action",
                       controller=copy_resources,
                       action='create',
                       conditions={"method": ['POST']})
        super(APIRouter, self).__init__(mapper)
