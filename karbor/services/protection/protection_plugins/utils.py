# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_service import loopingcall


def status_poll(get_status_func, interval, success_statuses=set(),
                failure_statuses=set(), ignore_statuses=set(),
                ignore_unexpected=False):
    def _poll():
        status = get_status_func()
        if status in success_statuses:
            raise loopingcall.LoopingCallDone(retvalue=True)
        if status in failure_statuses:
            raise loopingcall.LoopingCallDone(retvalue=False)
        if status in ignore_statuses:
            return
        if ignore_unexpected is False:
            raise loopingcall.LoopingCallDone(retvalue=False)

    loop = loopingcall.FixedIntervalLoopingCall(_poll)
    return loop.start(interval=interval, initial_delay=interval).wait()
