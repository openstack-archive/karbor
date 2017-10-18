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

GET_ALL_POLICY = 'service:get_all'
UPDATE_POLICY = 'service:update'

service_policies = [
    policy.DocumentedRuleDefault(
        name=GET_ALL_POLICY,
        check_str=base.RULE_ADMIN_API,
        description='List services.',
        operations=[
            {
                'method': 'GET',
                'path': '/os-services'
            }
        ]),
    policy.DocumentedRuleDefault(
        name=UPDATE_POLICY,
        check_str=base.RULE_ADMIN_API,
        description='Update service status',
        operations=[
            {
                'method': 'PUT',
                'path': '/os-services/{service_id}'
            }
        ]),
]


def list_rules():
    return service_policies
