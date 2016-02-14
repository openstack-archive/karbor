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


from oslo_config import cfg
from oslo_log import log as logging


CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class CheckpointSerializer(object):
    def __init__(self):
        super(CheckpointSerializer, self).__init__()
        # TODO(wangliuan)

    def serialize(self, checkpoint, encoding_format):
        # TODO(wangliuan)
        pass

    def deserialize(self, data, encoding_format):
        # TODO(wangliuan)
        pass


class CheckpointCollection(object):
    def __init__(self):
        super(CheckpointCollection, self).__init__()
        self.checkpoint_serializer = None
        self.bank_plugin = None
        # TODO(wangliuan)

    def list(self, list_options):
        # TODO(wangliuan)
        pass

    def show(self, checkpoint_id):
        # TODO(wangliuan)
        pass

    def delete(self, checkpoint_id):
        # TODO(wangliuan)
        pass

    def create(self, plan):
        # TODO(wangliuan)
        pass

    def update(self, checkpoint, **kwargs):
        # TODO(wangliuan)
        pass
