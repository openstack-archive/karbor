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


from smaug.tests.fullstack import smaug_base


class TriggersTest(smaug_base.SmaugBaseTest):
    """Test Triggers operation

    """
    def create_triggers(self):
        trigger1 = self.smaug_client.triggers.create(
            "My 1 Trigger", "time",
            {"pattern": "0 20 * * 2", "format": "crontab"})
        trigger2 = self.smaug_client.triggers.create(
            "My 2 Trigger", "time",
            {"pattern": "0 10 * * *", "format": "crontab"})
        return trigger1, trigger2

    def test_triggers_create(self):
        trigger1, trigger2 = self.create_triggers()
        trigger_item1 = self.smaug_client.triggers.get(trigger1.get("id"))
        trigger_item2 = self.smaug_client.triggers.get(trigger2.get("id"))
        trigger1_id = trigger_item1.id
        trigger2_id = trigger_item2.id
        self.assertEqual(trigger1_id, trigger1.get("id"))
        self.assertEqual(trigger2_id, trigger2.get("id"))
        self.smaug_client.triggers.delete(trigger1.get("id"))
        self.smaug_client.triggers.delete(trigger2.get("id"))

    def test_triggers_list(self):
        trigger1, trigger2 = self.create_triggers()
        triggers_item = self.smaug_client.triggers.list()
        self.assertEqual(2, len(triggers_item))
        self.smaug_client.triggers.delete(trigger1.get("id"))
        self.smaug_client.triggers.delete(trigger2.get("id"))

    def test_triggers_get(self):
        trigger1, trigger2 = self.create_triggers()
        trigger = self.smaug_client.triggers.get(trigger1.get("id"))
        self.assertEqual("My 1 Trigger", trigger.name)
        self.smaug_client.triggers.delete(trigger1.get("id"))
        self.smaug_client.triggers.delete(trigger2.get("id"))

    def test_triggers_delete(self):
        trigger1, trigger2 = self.create_triggers()
        trigger1_id = trigger1.get("id")
        self.smaug_client.triggers.delete(trigger1_id)
        triggers_item = self.smaug_client.triggers.list()
        self.assertEqual(1, len(triggers_item))
        self.smaug_client.triggers.delete(trigger2.get("id"))
