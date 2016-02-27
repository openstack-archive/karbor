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

#  operation type
OPERATION_PROTECT = 'protect'
OPERATION_RESTORE = 'restore'
OPERATION_START = 'start'
OPERATION_DELETE = 'delete'
OPERATION_SUSPEND = 'suspend'

# supported resource types
RESOURCE_TYPES = (PROJECT_RESOURCE_TYPE,
                  SERVER_RESOURCE_TYPE,
                  VOLUME_RESOURCE_TYPE,
                  ) = ('OS::Keystone::Project',
                       'OS::Nova::Server',
                       'OS::Cinder::Volume',
                       )
