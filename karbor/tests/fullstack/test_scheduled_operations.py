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

from datetime import datetime
from functools import partial

from karbor.common import constants
from karbor.services.operationengine.engine.triggers.timetrigger \
    .timeformats import calendar_time
from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects
from karbor.tests.fullstack import utils

pattern = "BEGIN:VEVENT\nRRULE:FREQ=WEEKLY;INTERVAL=1;\nEND:VEVENT"
DEFAULT_PROPERTY = {'pattern': pattern}


class ScheduledOperationsTest(karbor_base.KarborBaseTest):
    """Test Scheduled Operations operation

    """
    def setUp(self):
        super(ScheduledOperationsTest, self).setUp()
        providers = self.provider_list()
        self.assertTrue(len(providers))
        self.provider_id = self.provider_id_noop

    def _create_scheduled_operation(
            self,
            resources,
            trigger_properties=DEFAULT_PROPERTY,
            operation_name=None):
        plan = self.store(objects.Plan())
        plan.create(self.provider_id, resources)
        operation_definition = {'plan_id': plan.id,
                                'provider_id': self.provider_id}
        trigger = self.store(objects.Trigger())
        trigger.create('time', trigger_properties)

        operation = objects.ScheduledOperation()
        operation.create('protect', trigger.id,
                         operation_definition, operation_name)
        return operation

    def _create_for_volume(self,
                           trigger_properties=DEFAULT_PROPERTY,
                           operation_name=None):
        volume = self.store(objects.Volume())
        volume.create(1)
        return self._create_scheduled_operation([volume, ],
                                                trigger_properties,
                                                operation_name)

    def _create_for_server(self,
                           trigger_properties=DEFAULT_PROPERTY,
                           operation_name=None):
        server = self.store(objects.Server())
        server.create()
        return self._create_scheduled_operation([server, ],
                                                trigger_properties,
                                                operation_name)

    def test_scheduled_operations_create_no_scheduled(self):
        name = "KarborFullstack-Scheduled-Operation-no-scheduled"
        operation = self.store(self._create_for_volume(operation_name=name))

        item = self.karbor_client.scheduled_operations.get(operation.id)
        self.assertEqual(name, item.name)

        items = self.karbor_client.scheduled_operations.list()
        ids = [item_.id for item_ in items]
        self.assertTrue(operation.id in ids)

    @staticmethod
    def _wait_timestamp(pattern, start_time, freq):
        if not isinstance(freq, int) or freq <= 0:
            return 0

        cur_time = copy.deepcopy(start_time)
        cal_obj = calendar_time.ICal(start_time, pattern)
        for i in range(freq):
            next_time = cal_obj.compute_next_time(cur_time)
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
        pattern = "BEGIN:VEVENT\nRRULE:FREQ=MINUTELY;INTERVAL=5;\nEND:VEVENT"
        cur_property = {'pattern': pattern, 'format': 'calendar'}

        operation = self.store(self._create_for_volume(cur_property))
        start_time = datetime.now().replace(microsecond=0)
        sleep_time = self._wait_timestamp(pattern, start_time, freq)
        self.assertNotEqual(0, sleep_time)
        eventlet.sleep(sleep_time)

        items = self.karbor_client.checkpoints.list(self.provider_id)
        operation_item = self.karbor_client.scheduled_operations.get(
            operation.id)
        plan_id = operation_item.operation_definition["plan_id"]
        cps = filter(lambda x: x.protection_plan["id"] == plan_id, items)
        self.assertEqual(freq, len(cps))

        for cp in cps:
            utils.wait_until_true(
                partial(self._checkpoint_status,
                        cp.id,
                        constants.CHECKPOINT_STATUS_AVAILABLE),
                timeout=objects.LONG_TIMEOUT, sleep=objects.LONG_SLEEP
            )
            checkpoint = self.store(objects.Checkpoint())
            checkpoint._provider_id = self.provider_id
            checkpoint.id = cp.id

    def test_scheduled_operations_list(self):
        operation1 = self.store(self._create_for_volume())
        operation2 = self.store(self._create_for_server())

        items = self.karbor_client.scheduled_operations.list()
        ids = [item.id for item in items]
        self.assertTrue(operation1.id in ids)
        self.assertTrue(operation2.id in ids)

    def test_scheduled_operations_get(self):
        name = "KarborFullstack-Scheduled-Operation-Test-Get"
        operation = self._create_for_volume(operation_name=name)
        self.store(operation)

        item = self.karbor_client.scheduled_operations.get(operation.id)
        self.assertEqual(item.name, name)
        self.assertEqual(item.id, operation.id)

    def test_scheduled_operations_delete(self):
        name = "KarborFullstack-Scheduled-Operation-Test-Delete"
        operation = self._create_for_volume(operation_name=name)

        item = self.karbor_client.scheduled_operations.get(operation.id)
        self.assertEqual(name, item.name)

        operation.close()
        items = self.karbor_client.scheduled_operations.list()
        ids = [item_.id for item_ in items]
        self.assertTrue(operation.id not in ids)
