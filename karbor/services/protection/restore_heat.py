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
import yaml

from karbor.exception import InvalidOriginalId
from oslo_log import log as logging
from oslo_serialization import jsonutils

LOG = logging.getLogger(__name__)


class HeatResource(object):
    def __init__(self, resource_id, type):
        super(HeatResource, self).__init__()
        self.resource_id = resource_id
        self._type = type
        self._properties = {}

    def set_property(self, key, value):
        self._properties[key] = value

    def to_dict(self):
        resource_dict = {
            self.resource_id: {
                "type": self._type,
                "properties": self._properties
            }
        }
        return resource_dict


class HeatTemplate(object):
    heat_template_version = str(datetime.date(2015, 10, 15))
    description = "karbor restore template"

    def __init__(self):
        super(HeatTemplate, self).__init__()
        self._resources = []
        self._original_id_resource_map = {}
        self._original_id_parameter_map = {}

    def put_resource(self, original_id, heat_resource):
        self._resources.append(heat_resource)
        self._original_id_resource_map[original_id] = heat_resource.resource_id

    def put_parameter(self, original_id, parameter):
        self._original_id_parameter_map[original_id] = parameter

    def get_resource_reference(self, original_id):
        if original_id in self._original_id_resource_map:
            return {
                "get_resource": (self._original_id_resource_map[original_id])
            }
        elif original_id in self._original_id_parameter_map:
            return self._original_id_parameter_map[original_id]
        else:
            LOG.error("The reference is not found, original_id:%s",
                      original_id)
            raise InvalidOriginalId

    def len(self):
        return len(self._resources)

    def to_dict(self):
        resources_dict = {}
        for resource in self._resources:
            resource_id = resource.resource_id
            resource_dict = resource.to_dict()
            resources_dict[resource_id] = resource_dict[resource_id]
        template_dict = {
            "heat_template_version": self.heat_template_version,
            "description": self.description,
            "resources": resources_dict
        }
        return yaml.load(jsonutils.dumps(template_dict))

    def dump_to_yaml_file(self, file_name):
        with open(file_name, "w") as f:
            yaml.dump(yaml.load(jsonutils.dumps(self.to_dict())),
                      f,
                      default_flow_style=False)
