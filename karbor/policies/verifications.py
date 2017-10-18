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


CREATE_POLICY = 'verification:create'
GET_POLICY = 'verification:get'
GET_ALL_POLICY = 'verification:get_all'

verifications_policies = [
    policy.DocumentedRuleDefault(
        name=CREATE_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Create a verification.',
        operations=[
            {
                'method': 'POST',
                'path': '/verifications'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get a verification.',
        operations=[
            {
                'method': 'GET',
                'path': '/verifications/{verification_id}'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_OR_OWNER,
        description='Get verifications.',
        operations=[
            {
                'method': 'GET',
                'path': '/verifications'
            }
        ]),
]


def list_rules():
    return verifications_policies
