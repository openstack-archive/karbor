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

import copy
import eventlet

from croniter import croniter
from datetime import datetime
from functools import partial

from karbor.common import constants
from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects
from karbor.tests.fullstack import utils

DEFAULT_PROPERTY = {'pattern': '0 20 * * 2', 'format': 'crontab'}


class ScheduledOperationsTest(karbor_base.KarborBaseTest):
    """Test Scheduled Operations operation

    """
    def setUp(self):
        super(ScheduledOperationsTest, self).setUp()
        providers = self.provider_list()
        self.assertTrue(len(providers))
        self.provider_id = self.provider_id_noop

    def _create_scheduled_operation(self,
                                    trigger_properties,
                                    operation_definition,
                                    operation_name=None):
        trigger = self.store(objects.Trigger())
        trigger.create('time', trigger_properties)

        operation = objects.ScheduledOperation()
        operation.create('protect', trigger.id,
                         operation_definition, operation_name)
        return operation

    def _create_scheduled_operation_for_volume(
            self,
            trigger_properties=DEFAULT_PROPERTY,
            operation_name=None):
        volume = self.store(objects.Volume())
        volume.create(1)
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [volume, ])
        operation_definition = {'plan_id': plan.id,
                                'provider_id': self.provider_id}
        return self._create_scheduled_operation(trigger_properties,
                                                operation_definition,
                                                operation_name)

    def _create_scheduled_operation_for_server(
            self,
            trigger_properties=DEFAULT_PROPERTY,
            operation_name=None):
        server = self.store(objects.Server())
        server.create()
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, [server, ])
        operation_definition = {'plan_id': plan.id,
                                'provider_id': self.provider_id}
        return self._create_scheduled_operation(trigger_properties,
                                                operation_definition,
                                                operation_name)

    def test_scheduled_operations_create_no_scheduled(self):
        operation_items = self.karbor_client.scheduled_operations.list()
        before_num = len(operation_items)

        self.store(self._create_scheduled_operation_for_volume())

        operation_items = self.karbor_client.scheduled_operations.list()
        after_num = len(operation_items)
        self.assertEqual(1, after_num - before_num)

    @staticmethod
    def _wait_timestamp(pattern, start_time, freq):
        if not isinstance(freq, int) or freq <= 0:
            return 0

        cur_time = copy.deepcopy(start_time)
        for i in range(freq):
            next_time = croniter(pattern, cur_time).get_next(datetime)
            cur_time = next_time
        return (next_time - start_time).seconds

    def _checkpoint_status(self, checkpoint_id, status):
        try:
            cp = self.karbor_client.checkpoints.get(self.provider_id,
                                                    checkpoint_id)
        except Exception:
            return False

        if status is None or cp.status == status:
            return True
        else:
            return False

    def test_scheduled_operations_create_and_scheduled(self):
        freq = 2
        pattern = '*/15 * * * *'
        cur_property = {'pattern': pattern, 'format': 'crontab'}

        before_items = self.karbor_client.checkpoints.list(self.provider_id)
        before_num = len(before_items)

        start_time = datetime.now().replace(microsecond=0)
        self.store(self._create_scheduled_operation_for_volume(cur_property))
        sleep_time = self._wait_timestamp(pattern, start_time, freq)
        self.assertNotEqual(0, sleep_time)
        eventlet.sleep(sleep_time)

        after_items = self.karbor_client.checkpoints.list(self.provider_id)
        after_num = len(after_items)
        self.assertEqual(freq, after_num - before_num)

        for item in after_items:
            if item not in before_items:
                utils.wait_until_true(
                    partial(self._checkpoint_status,
                            item.id,
                            constants.CHECKPOINT_STATUS_AVAILABLE),
                    timeout=objects.LONG_TIMEOUT, sleep=objects.LONG_SLEEP
                )
                self.karbor_client.checkpoints.delete(self.provider_id,
                                                      item.id)

    def test_scheduled_operations_list(self):
        operation_items = self.karbor_client.scheduled_operations.list()
        before_num = len(operation_items)

        self.store(self._create_scheduled_operation_for_volume())
        self.store(self._create_scheduled_operation_for_server())

        operation_items = self.karbor_client.scheduled_operations.list()
        after_num = len(operation_items)
        self.assertEqual(2, after_num - before_num)

    def test_scheduled_operations_get(self):
        operation_name = "KarborFullstack-Scheduled-Operation-Test-Get"
        operation = self._create_scheduled_operation_for_volume(
            operation_name=operation_name
        )
        self.store(operation)

        operation_item = self.karbor_client.scheduled_operations.get(
            operation.id
        )
        self.assertEqual(operation_item.name, operation_name)
        self.assertEqual(operation_item.id, operation.id)

    def test_scheduled_operations_delete(self):
        operation_items = self.karbor_client.scheduled_operations.list()
        before_num = len(operation_items)

        operation_name = "KarborFullstack-Scheduled-Operation-Test-Delete"
        operation = self._create_scheduled_operation_for_volume(
            operation_name=operation_name
        )

        operation_item = self.karbor_client.scheduled_operations.get(
            operation.id
        )
        self.assertEqual(operation_name, operation_item.name)

        operation.close()
        operation_items = self.karbor_client.scheduled_operations.list()
        after_num = len(operation_items)
        self.assertEqual(before_num, after_num)
