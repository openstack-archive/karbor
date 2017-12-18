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
Schema for Karbor V1 Triggers API.

"""


create = {
    'type': 'object',
    'properties': {
        'type': 'object',
        'trigger_info': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'type': {'type': 'string'},
                'properties': {
                    'type': 'object',
                    'properties': {
                        'format': {'type': 'string'},
                        'pattern': {'type': 'string'},
                        'start_time': {'type': 'string'},
                        'end_time': {'type': 'string'},
                        'window': {'type': 'integer'},
                    },
                    'required': ['format', 'pattern'],
                    'additionalProperties': False,
                },
            },
            'required': ['name', 'type', 'properties'],
            'additionalProperties': False,
        },
    },
    'required': ['trigger_info'],
    'additionalProperties': False,
}


update = {
    'type': 'object',
    'properties': {
        'type': 'object',
        'trigger_info': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'type': {'type': 'string'},
                'properties': {
                    'type': 'object',
                    'properties': {
                        'format': {'type': 'string'},
                        'pattern': {'type': 'string'},
                        'start_time': {'type': 'string'},
                        'end_time': {'type': 'string'},
                        'window': {'type': 'integer'},
                    },
                    'required': [],
                    'additionalProperties': False,
                },
            },
            'required': [],
            'additionalProperties': False,
        },
    },
    'required': ['trigger_info'],
    'additionalProperties': False,
}
