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
Schema for Karbor V1 Checkpoints API.

"""

from karbor.api.validation import parameter_types


create = {
    'type': 'object',
    'properties': {
        'type': 'object',
        'checkpoint': {
            'type': 'object',
            'properties': {
                'plan_id': parameter_types.uuid,
                'extra-info': parameter_types.metadata,
            },
            'required': ['plan_id'],
            'additionalProperties': False,
        },
    },
    'required': ['checkpoint'],
    'additionalProperties': False,
}

update = {
    'type': 'object',
    'properties': {
        'type': 'object',
        'os-resetState': {
            'type': 'object',
            'properties': {
                'state': {
                    'type': 'string',
                    'enum': ['available', 'error'],
                },
            },
            'required': ['state'],
            'additionalProperties': False,
        },
    },
    'required': ['os-resetState'],
    'additionalProperties': False,
}
