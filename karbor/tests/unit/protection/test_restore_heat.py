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

import datetime
import tempfile
import yaml

from karbor.services.protection.restore_heat import HeatResource
from karbor.services.protection.restore_heat import HeatTemplate
from karbor.tests import base


class HeatResourceTest(base.TestCase):
    def setUp(self):
        super(HeatResourceTest, self).setUp()
        fake_resource_id = "restore_123456"
        fake_resource_type = "OS::Cinder::Volume"
        self.heat_resource = HeatResource(fake_resource_id, fake_resource_type)

    def test_set_property(self):
        key = "volume_type"
        value = "lvmdriver-1"
        self.heat_resource.set_property(key, value)
        self.assertEqual({"volume_type": "lvmdriver-1"},
                         self.heat_resource._properties)

    def test_to_dict(self):
        properties = {
            "volume_type": "lvmdriver-1",
            "size": 1
        }
        for key, value in properties.items():
            self.heat_resource.set_property(key, value)
        resource_dict = self.heat_resource.to_dict()

        target_dict = {
            "restore_123456": {
                "type": "OS::Cinder::Volume",
                "properties": {
                    "volume_type": "lvmdriver-1",
                    "size": 1
                }
            }
        }
        self.assertEqual(target_dict, resource_dict)

    def tearDown(self):
        super(HeatResourceTest, self).tearDown()


class HeatTemplateTest(base.TestCase):
    def setUp(self):
        super(HeatTemplateTest, self).setUp()
        self.heat_template = HeatTemplate()

    def test_put_resource(self):
        fake_original_id = "123456"
        fake_resource_id = "restore_123456"
        fake_resource_type = "OS::Cinder::Volume"
        heat_resource = HeatResource(fake_resource_id, fake_resource_type)
        properties = {
            "volume_type": "lvmdriver-1",
            "size": 1
        }
        for key, value in properties.items():
            heat_resource.set_property(key, value)
        self.heat_template.put_resource(fake_original_id, heat_resource)
        self.assertEqual(1, len(self.heat_template._resources))
        self.assertEqual(
            fake_resource_id,
            self.heat_template._original_id_resource_map[fake_original_id]
        )

    def test_put_parameter(self):
        fake_original_id = "123456"
        fake_parameter = "restored_123456"
        self.heat_template.put_parameter(fake_original_id, fake_parameter)
        self.assertEqual(1, len(self.heat_template._original_id_parameter_map))
        self.assertEqual(
            fake_parameter,
            self.heat_template._original_id_parameter_map[fake_original_id]
        )

    def test_get_resource_reference(self):
        fake_original_id = "123456"
        fake_resource_id = "restore_123456"
        fake_resource_type = "OS::Cinder::Volume"
        heat_resource = HeatResource(fake_resource_id, fake_resource_type)
        properties = {
            "volume_type": "lvmdriver-1",
            "size": 1
        }
        for key, value in properties.items():
            heat_resource.set_property(key, value)
        self.heat_template.put_resource(fake_original_id, heat_resource)

        reference = self.heat_template.get_resource_reference(fake_original_id)
        self.assertEqual({"get_resource": "restore_123456"}, reference)

        fake_original_id = '23456'
        fake_parameter = 'restored_23456'
        self.heat_template.put_parameter(fake_original_id, fake_parameter)
        reference = self.heat_template.get_resource_reference(fake_original_id)
        self.assertEqual(fake_parameter, reference)

    def test_to_dict(self):
        fake_original_id = "123456"
        fake_resource_id = "restore_123456"
        fake_resource_type = "OS::Cinder::Volume"
        heat_resource = HeatResource(fake_resource_id, fake_resource_type)
        properties = {
            "volume_type": "lvmdriver-1",
            "size": 1
        }
        for key, value in properties.items():
            heat_resource.set_property(key, value)
        self.heat_template.put_resource(fake_original_id, heat_resource)

        fake_original_id_2 = '23456'
        fake_parameter = 'restored_23456'
        self.heat_template.put_parameter(fake_original_id_2, fake_parameter)

        template_dict = self.heat_template.to_dict()

        target_dict = {
            "heat_template_version": str(datetime.date(2015, 10, 15)),
            "description": "karbor restore template",
            "resources": {
                "restore_123456": {
                    "type": "OS::Cinder::Volume",
                    "properties": {
                        "volume_type": "lvmdriver-1",
                        "size": 1
                    }
                }
            }
        }
        self.assertEqual(target_dict, template_dict)

    def test_dump_to_yaml_file(self):
        fake_original_id = "123456"
        temp_dir = tempfile.mkdtemp()
        temp_file = temp_dir + "/template.yaml"

        fake_resource_id = "restore_123456"
        fake_resource_type = "OS::Cinder::Volume"
        heat_resource = HeatResource(fake_resource_id, fake_resource_type)
        properties = {
            "volume_type": "lvmdriver-1",
            "size": 1
        }
        for key, value in properties.items():
            heat_resource.set_property(key, value)
        self.heat_template.put_resource(fake_original_id, heat_resource)

        self.heat_template.dump_to_yaml_file(temp_file)

        with open(temp_file, "r") as f:
            template_dict = yaml.load(f)
        target_dict = {
            "heat_template_version": str(datetime.date(2015, 10, 15)),
            "description": "karbor restore template",
            "resources": {
                "restore_123456": {
                    "type": "OS::Cinder::Volume",
                    "properties": {
                        "volume_type": "lvmdriver-1",
                        "size": 1
                    }
                }
            }
        }
        self.assertEqual(target_dict, template_dict)
