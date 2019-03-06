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

"""
Schema for Karbor V1 scheduled operations API.

"""

from karbor.api.validation import parameter_types


create = {
    'type': 'object',
    'properties': {
        'type': 'object',
        'scheduled_operation': {
            'type': 'object',
            'properties': {
                'name': parameter_types.name,
                'description': parameter_types.description,
                'operation_type': {'type': 'string'},
                'trigger_id': parameter_types.uuid,
                'operation_definition': {
                    'type': 'object',
                    'properties': {
                        'provider_id': parameter_types.uuid,
                        'plan_id': parameter_types.uuid,
                    },
                    'required': ['provider_id', 'plan_id'],
                    'additionalProperties': True,
                },

            },
            'required': ['operation_type', 'trigger_id',
                         'operation_definition'],
            'additionalProperties': False,
        },
    },
    'required': ['scheduled_operation'],
    'additionalProperties': False,
}
