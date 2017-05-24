# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.


from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import importutils

from karbor.common import constants
from karbor import exception
from karbor.services.protection.flows import delete as flow_delete
from karbor.services.protection.flows import protect as flow_protect
from karbor.services.protection.flows import restore as flow_restore

workflow_opts = [
    cfg.StrOpt(
        'workflow_engine',
        default="karbor.services.protection.flows.workflow.TaskFlowEngine",
        help='The workflow engine provides *flow* and *task* interface')
]

LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.register_opts(workflow_opts)


class Worker(object):
    def __init__(self, engine_path=None):
        super(Worker, self).__init__()
        try:
            self.workflow_engine = self._load_engine(engine_path)
        except Exception:
            LOG.error("load work flow engine failed")
            raise

    def _load_engine(self, engine_path):
        if not engine_path:
            engine_path = CONF.workflow_engine
        engine = importutils.import_object(engine_path)
        return engine

    def get_flow(self, context, operation_type, checkpoint, provider,
                 **kwargs):
        if operation_type == constants.OPERATION_PROTECT:
            plan = kwargs.get('plan', None)
            protectable_registry = kwargs.get('protectable_registry', None)
            flow = flow_protect.get_flow(
                context,
                protectable_registry,
                self.workflow_engine,
                plan,
                provider,
                checkpoint,
            )
        elif operation_type == constants.OPERATION_RESTORE:
            restore = kwargs.get('restore')
            restore_auth = kwargs.get('restore_auth')
            flow = flow_restore.get_flow(
                context,
                self.workflow_engine,
                checkpoint,
                provider,
                restore,
                restore_auth,
            )
        elif operation_type == constants.OPERATION_DELETE:
            flow = flow_delete.get_flow(
                context,
                self.workflow_engine,
                checkpoint,
                provider,
            )
        else:
            raise exception.InvalidParameterValue(
                err='unknown operation type %s' % operation_type
            )

        return flow

    def run_flow(self, flow_engine):
        self.workflow_engine.run_engine(flow_engine)

    def flow_outputs(self, flow_engine, target=None):
        return self.workflow_engine.output(flow_engine, target=target)
