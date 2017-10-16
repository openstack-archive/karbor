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


CREATE_POLICY = 'plan:create'
UPDATE_POLICY = 'plan:update'
DELETE_POLICY = 'plan:delete'
GET_POLICY = 'plan:get'
GET_ALL_POLICY = 'plan:get_all'

plans_policies = [
    policy.DocumentedRuleDefault(
        name=CREATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a plan.',
        operations=[
            {
                'method': 'POST',
                'path': '/plans'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=UPDATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Update a plan.',
        operations=[
            {
                'method': 'PUT',
                'path': '/plans/{plan_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=DELETE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a plan.',
        operations=[
            {
                'method': 'DELETE',
                'path': '/plans/{plan_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get a plan.',
        operations=[
            {
                'method': 'GET',
                'path': '/plans/{plan_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get plans.',
        operations=[
            {
                'method': 'GET',
                'path': '/plans'
            }
        ]),
]


def list_rules():
    return plans_policies
