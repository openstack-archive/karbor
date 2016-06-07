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
import abc

import six

from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ProtectionPlugin(object):
    def __init__(self, config=None):
        self._config = config

    @abc.abstractmethod
    def get_supported_resources_types(self):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def get_options_schema(self, resources_type):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def get_saved_info_schema(self, resources_type):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def get_restore_schema(self, resources_type):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def get_saved_info(self, metadata_store, resource):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def get_resource_stats(self, checkpoint, resource_id):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def on_resource_start(self, context):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def on_resource_end(self, context):
        # TODO(wangliuan)
        pass
