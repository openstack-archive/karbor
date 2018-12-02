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


GET_POLICY = 'provider:get'
GET_ALL_POLICY = 'provider:get_all'
CHECKPOINT_GET_POLICY = 'provider:checkpoint_get'
CHECKPOINT_GET_ALL_POLICY = 'provider:checkpoint_get_all'
CHECKPOINT_CREATE_POLICY = 'provider:checkpoint_create'
CHECKPOINT_DELETE_POLICY = 'provider:checkpoint_delete'
CHECKPOINT_UPDATE_POLICY = 'provider:checkpoint_update'


providers_policies = [
    policy.DocumentedRuleDefault(
        name=GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Show a protection provider.',
        operations=[
            {
                'method': 'GET',
                'path': '/providers/{provider_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List protection providers.',
        operations=[
            {
                'method': 'GET',
                'path': '/providers'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=CHECKPOINT_GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Show a checkpoint.',
        operations=[
            {
                'method': 'GET',
                'path': '/providers/{provider_id}/checkpoints/{checkpoint_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=CHECKPOINT_GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List checkpoints.',
        operations=[
            {
                'method': 'GET',
                'path': '/providers/{provider_id}/checkpoints'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=CHECKPOINT_CREATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create checkpoint.',
        operations=[
            {
                'method': 'POST',
                'path': '/providers/{provider_id}/checkpoints'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=CHECKPOINT_DELETE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Delete checkpoint.',
        operations=[
            {
                'method': 'DELETE',
                'path': '/providers/{provider_id}/checkpoints/{checkpoint_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=CHECKPOINT_UPDATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Reset checkpoint state.',
        operations=[
            {
                'method': 'PUT',
                'path': '/providers/{provider_id}/checkpoints/{checkpoint_id}'
            }
        ]
    )
]


def list_rules():
    return providers_policies
