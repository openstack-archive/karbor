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

from smaug.api.openstack import ProjectMapper
from smaug.api.v1 import plans
from smaug.api.v1 import scheduled_operations
from smaug.wsgi import common as wsgi_common


class APIRouter(wsgi_common.Router):
    @classmethod
    def factory(cls, global_conf, **local_conf):
        return cls(ProjectMapper())

    def __init__(self, mapper):
        plans_resources = plans.create_resource()
        scheduled_operation_resources = scheduled_operations.create_resource()
        mapper.resource("plan", "plans",
                        controller=plans_resources,
                        collection={},
                        member={'action': 'POST'})
        mapper.resource("scheduled_operation", "scheduled_operations",
                        controller=scheduled_operation_resources,
                        collection={'detail': 'GET'},
                        member={'action': 'POST'})
        super(APIRouter, self).__init__(mapper)
