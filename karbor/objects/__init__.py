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


def register_all():
    # You must make sure your object gets imported in this
    # function in order for it to be registered by services that may
    # need to receive it via RPC.
    __import__('karbor.objects.service')
    __import__('karbor.objects.plan')
    __import__('karbor.objects.scheduled_operation')
    __import__('karbor.objects.trigger')
    __import__('karbor.objects.scheduled_operation_log')
    __import__('karbor.objects.scheduled_operation_state')
    __import__('karbor.objects.restore')
    __import__('karbor.objects.operation_log')
    __import__('karbor.objects.checkpoint_record')
