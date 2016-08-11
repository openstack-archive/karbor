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


class SyncCheckpointStatusTask(task.Task):
    def __init__(self, checkpoint, status_getters):
        super(SyncCheckpointStatusTask, self).__init__()
        self._status_getters = status_getters
        self._checkpoint = checkpoint

    def execute(self):
        LOG.info(_("Start sync checkpoint status,checkpoint_id:%s"),
                 self._checkpoint.id)
        sync_status = loopingcall.FixedIntervalLoopingCall(
            self._sync_status, self._checkpoint, self._status_getters)
        sync_status.start(interval=CONF.sync_status_interval)

    def _sync_status(self, checkpoint, status_getters):
        status = {}
        for s in status_getters:
            resource_id = s.get('resource_id')
            get_resource_stats = s.get('get_resource_stats')
            status[resource_id] = get_resource_stats(checkpoint,
                                                     resource_id)
        list_status = list(set(status.values()))
        LOG.info(_("Start sync checkpoint status,checkpoint_id:"
                   "%(checkpoint_id)s, resource_status:"
                   "%(resource_status)s") %
                 {"checkpoint_id": checkpoint.id,
                  "resource_status": status})
        if constants.RESOURCE_STATUS_ERROR in list_status:
            checkpoint.status = constants.CHECKPOINT_STATUS_ERROR_DELETING
            checkpoint.commit()
            raise loopingcall.LoopingCallDone()
        elif [constants.RESOURCE_STATUS_DELETED] == list_status:
            checkpoint.delete()
            LOG.info(_("Stop sync checkpoint status,checkpoint_id:"
                       "%(checkpoint_id)s,checkpoint status:"
                       "%(checkpoint_status)s") %
                     {"checkpoint_id": checkpoint.id,
                      "checkpoint_status": checkpoint.status})
            raise loopingcall.LoopingCallDone()


def get_flow(context, workflow_engine, operation_type, checkpoint, provider):

    ctx = {'context': context,
           'checkpoint': checkpoint,
           'workflow_engine': workflow_engine,
           'operation_type': operation_type,
           }
    LOG.info(_("Start get checkpoint flow,checkpoint_id:%s"),
             checkpoint.id)
    flow_name = "delete_checkpoint_" + checkpoint.id
    delete_flow = workflow_engine.build_flow(flow_name, 'linear')
    result = provider.build_task_flow(ctx)
    status_getters = result.get('status_getters')
    resource_flow = result.get('task_flow')
    workflow_engine.add_tasks(delete_flow,
                              resource_flow,
                              SyncCheckpointStatusTask(checkpoint,
                                                       status_getters))
    flow_engine = workflow_engine.get_engine(delete_flow)
    return flow_engine
