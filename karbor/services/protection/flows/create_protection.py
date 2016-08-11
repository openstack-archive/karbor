# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from karbor.common import constants
from karbor.i18n import _
from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import loopingcall
from taskflow import task

sync_status_opts = [
    cfg.IntOpt('sync_status_interval',
               default=60,
               help='update protection status interval')
]

CONF = cfg.CONF
CONF.register_opts(sync_status_opts)

LOG = logging.getLogger(__name__)


class CreateCheckpointTask(task.Task):
    def __init__(self, plan, provider, resource_graph):
        provides = 'checkpoint'
        super(CreateCheckpointTask, self).__init__(provides=provides)
        self._plan = plan
        self._provider = provider
        self._resource_graph = resource_graph

    def execute(self):
        checkpoint_collection = self._provider.get_checkpoint_collection()
        checkpoint = checkpoint_collection.create(self._plan)
        checkpoint.resource_graph = self._resource_graph
        checkpoint.commit()
        return checkpoint


class SyncCheckpointStatusTask(task.Task):
    def __init__(self, status_getters):
        requires = ['checkpoint']
        super(SyncCheckpointStatusTask, self).__init__(requires=requires)
        self._status_getters = status_getters

    def execute(self, checkpoint):
        LOG.info(_("Start sync checkpoint status,checkpoint_id:%s"),
                 checkpoint.id)
        sync_status = loopingcall.FixedIntervalLoopingCall(
            self._sync_status, checkpoint, self._status_getters)
        sync_status.start(interval=CONF.sync_status_interval)

    def _sync_status(self, checkpoint, status_getters):
        status = {}
        for s in status_getters:
            resource_id = s.get('resource_id')
            get_resource_stats = s.get('get_resource_stats')
            status[resource_id] = get_resource_stats(checkpoint,
                                                     resource_id)
        if constants.RESOURCE_STATUS_ERROR in status.values():
            checkpoint.status = constants.CHECKPOINT_STATUS_ERROR
            checkpoint.commit()
        elif constants.RESOURCE_STATUS_PROTECTING in status.values():
            checkpoint.status = constants.CHECKPOINT_STATUS_PROTECTING
            checkpoint.commit()
        elif constants.RESOURCE_STATUS_UNDEFINED in status.values():
            checkpoint.status = constants.CHECKPOINT_STATUS_PROTECTING
            checkpoint.commit()
        else:
            checkpoint.status = constants.CHECKPOINT_STATUS_AVAILABLE
            checkpoint.commit()
            LOG.info(_("Stop sync checkpoint status,checkpoint_id:"
                       "%(checkpoint_id)s,checkpoint status:"
                       "%(checkpoint_status)s") %
                     {"checkpoint_id": checkpoint.id,
                      "checkpoint_status": checkpoint.status})
            raise loopingcall.LoopingCallDone()


def get_flow(context, workflow_engine, operation_type, plan, provider):
    ctx = {'context': context,
           'plan': plan,
           'workflow_engine': workflow_engine,
           'operation_type': operation_type}
    flow_name = "create_protection_" + plan.get('id')
    protection_flow = workflow_engine.build_flow(flow_name, 'linear')
    result = provider.build_task_flow(ctx)
    status_getters = result.get('status_getters')
    resource_flow = result.get('task_flow')
    resource_graph = result.get('resource_graph')
    workflow_engine.add_tasks(protection_flow,
                              CreateCheckpointTask(plan, provider,
                                                   resource_graph),
                              resource_flow,
                              SyncCheckpointStatusTask(status_getters))
    flow_engine = workflow_engine.get_engine(protection_flow)
    return flow_engine
