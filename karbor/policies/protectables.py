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


GET_POLICY = 'protectable:get'
GET_ALL_POLICY = 'protectable:get_all'
INSTANCES_GET_POLICY = 'protectable:instance_get'
INSTANCES_GET_ALL_POLICY = 'protectable:instance_get_all'

protectables_policies = [
    policy.DocumentedRuleDefault(
        name=GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Show a protectable type.',
        operations=[
            {
                'method': 'GET',
                'path': '/protectables/{protectable_type}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List protectable types.',
        operations=[
            {
                'method': 'GET',
                'path': '/protectables'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=INSTANCES_GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Show a protectable instance.',
        operations=[
            {
                'method': 'GET',
                'path': '/protectables/{protectable_type}/'
                        'instances/{resource_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=INSTANCES_GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='List protectable instances.',
        operations=[
            {
                'method': 'GET',
                'path': '/protectables/{protectable_type}/instances'
            }
        ]),
]


def list_rules():
    return protectables_policies
