# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import eventlet


def wait_until_true(predicate, timeout=60, sleep=1, exception=None):
    """Wait until callable predicate is evaluated as True

    :param predicate: Callable deciding whether waiting should continue.
    Best practice is to instantiate predicate with functools.partial()
    :param timeout: Timeout in seconds how long should function wait.
    :param sleep: Polling interval for results in seconds.
    :param exception: Exception class for eventlet.Timeout.
    (see doc for eventlet.Timeout for more information)

    """
    with eventlet.timeout.Timeout(timeout, exception):
        while not predicate():
            eventlet.sleep(sleep)


def wait_until_is_and_return(predicate, timeout=5, sleep=1, exception=None):
    container = {}

    def internal_predicate():
        container['value'] = predicate()
        return container['value']

    wait_until_true(internal_predicate, timeout, sleep, exception)
    return container.get('value')


def wait_until_none(predicate, timeout=5, sleep=1, exception=None):
    def internal_predicate():
        ret = predicate()
        if ret:
            return False
        return True
    wait_until_true(internal_predicate, timeout, sleep, exception)
