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


CREATE_POLICY = 'trigger:create'
UPDATE_POLICY = 'trigger:update'
DELETE_POLICY = 'trigger:delete'
GET_POLICY = 'trigger:get'
GET_ALL_POLICY = 'trigger:list'

triggers_policies = [
    policy.DocumentedRuleDefault(
        name=CREATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a trigger.',
        operations=[
            {
                'method': 'POST',
                'path': '/triggers'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=UPDATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Update a trigger.',
        operations=[
            {
                'method': 'PUT',
                'path': '/triggers/{trigger_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=DELETE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete a trigger.',
        operations=[
            {
                'method': 'DELETE',
                'path': '/triggers/{trigger_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get a trigger.',
        operations=[
            {
                'method': 'GET',
                'path': '/triggers/{trigger_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get triggerss.',
        operations=[
            {
                'method': 'GET',
                'path': '/triggers'
            }
        ]),
]


def list_rules():
    return triggers_policies
