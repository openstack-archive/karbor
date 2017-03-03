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


from karbor.tests.fullstack import karbor_base
from karbor.tests.fullstack import karbor_objects as objects


class TriggersTest(karbor_base.KarborBaseTest):
    """Test Triggers operation"""

    def test_triggers_list(self):
        pattern1 = "BEGIN:VEVENT\nRRULE:FREQ=HOURLY;INTERVAL=1;\nEND:VEVENT"
        trigger1 = self.store(objects.Trigger())
        trigger1.create('time', {'pattern': pattern1, 'format': 'calendar'})
        pattern2 = "BEGIN:VEVENT\nRRULE:FREQ=WEEKLY;INTERVAL=1;\nEND:VEVENT"
        trigger2 = self.store(objects.Trigger())
        trigger2.create('time', {'pattern': pattern2, 'format': 'calendar'})

        items = self.karbor_client.triggers.list()
        ids = [item.id for item in items]
        self.assertTrue(trigger1.id in ids)
        self.assertTrue(trigger2.id in ids)

    def test_triggers_get(self):
        trigger_name = "FullStack Trigger Test Get"
        pattern = "BEGIN:VEVENT\nRRULE:FREQ=WEEKLY;INTERVAL=1;\nEND:VEVENT"
        trigger = self.store(objects.Trigger())
        trigger.create('time', {'pattern': pattern, 'format': 'calendar'},
                       name=trigger_name)
        trigger = self.karbor_client.triggers.get(trigger.id)
        self.assertEqual(trigger_name, trigger.name)

    def test_triggers_delete(self):
        pattern = "BEGIN:VEVENT\nRRULE:FREQ=WEEKLY;INTERVAL=1;\nEND:VEVENT"
        trigger = objects.Trigger()
        trigger.create('time', {'pattern': pattern, 'format': 'calendar'})
        self.karbor_client.triggers.delete(trigger.id)
        items = self.karbor_client.triggers.list()
        ids = [item.id for item in items]
        self.assertTrue(trigger.id not in ids)
