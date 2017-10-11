# Copyright (c) 2017 Huawei Technologies Co., Ltd.
# All Rights Reserved.
#
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

from oslo_policy import policy

from karbor.policies import base


CREATE_POLICY = 'scheduled_operation:create'
DELETE_POLICY = 'scheduled_operation:delete'
GET_POLICY = 'scheduled_operation:get'
GET_ALL_POLICY = 'scheduled_operation:list'

scheduled_operations_policies = [
    policy.DocumentedRuleDefault(
        name=CREATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a scheduled_operation.',
        operations=[
            {
                'method': 'POST',
                'path': '/scheduled_operations'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=DELETE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a scheduled_operation.',
        operations=[
            {
                'method': 'DELETE',
                'path': '/scheduled_operations/{scheduled_operation_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get a scheduled_operation.',
        operations=[
            {
                'method': 'GET',
                'path': '/scheduled_operations/{scheduled_operation_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get scheduled_operations.',
        operations=[
            {
                'method': 'GET',
                'path': '/scheduled_operations'
            }
        ]),
]


def list_rules():
    return scheduled_operations_policies
