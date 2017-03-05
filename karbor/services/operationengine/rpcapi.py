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

"""
Client side of the OperationEngine manager RPC API.
"""

from oslo_config import cfg
import oslo_messaging as messaging

from karbor.objects import base as objects_base
from karbor import rpc


CONF = cfg.CONF


class OperationEngineAPI(object):
    """Client side of the OperationEngine rpc API.

    API version history:

        1.0 - Initial version.
    """

    RPC_API_VERSION = '1.0'

    def __init__(self):
        super(OperationEngineAPI, self).__init__()
        target = messaging.Target(topic=CONF.operationengine_topic,
                                  version=self.RPC_API_VERSION)
        serializer = objects_base.KarborObjectSerializer()

        client = rpc.get_client(target, version_cap=None,
                                serializer=serializer)
        self._client = client.prepare(version='1.0')

    def create_scheduled_operation(self, ctxt, operation):
        return self._client.call(ctxt, 'create_scheduled_operation',
                                 operation=operation)

    def delete_scheduled_operation(self, ctxt, operation_id, trigger_id):
        return self._client.call(ctxt, 'delete_scheduled_operation',
                                 operation_id=operation_id,
                                 trigger_id=trigger_id)

    def suspend_scheduled_operation(self, ctxt, operation_id, trigger_id):
        return self._client.call(ctxt, 'suspend_scheduled_operation',
                                 operation_id=operation_id,
                                 trigger_id=trigger_id)

    def resume_scheduled_operation(self, ctxt, operation_id, trigger_id):
        return self._client.call(ctxt, 'resume_scheduled_operation',
                                 operation_id=operation_id,
                                 trigger_id=trigger_id)

    def create_trigger(self, ctxt, trigger):
        return self._client.call(ctxt, 'create_trigger', trigger=trigger)

    def delete_trigger(self, ctxt, trigger_id):
        return self._client.call(ctxt, 'delete_trigger', trigger_id=trigger_id)

    def update_trigger(self, ctxt, trigger):
        return self._client.call(ctxt, 'update_trigger', trigger=trigger)
