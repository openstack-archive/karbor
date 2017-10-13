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

import itertools

from karbor.policies import base
from karbor.policies import operation_logs
from karbor.policies import plans
from karbor.policies import protectables
from karbor.policies import providers
from karbor.policies import restores
from karbor.policies import scheduled_operations
from karbor.policies import triggers


def list_rules():
    return itertools.chain(
        base.list_rules(),
        plans.list_rules(),
        restores.list_rules(),
        protectables.list_rules(),
        providers.list_rules(),
        triggers.list_rules(),
        scheduled_operations.list_rules(),
        operation_logs.list_rules(),
    )
