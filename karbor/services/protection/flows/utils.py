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
from karbor import exception
from karbor.i18n import _
from karbor import objects
from karbor.objects import base as objects_base
from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import timeutils

LOG = logging.getLogger(__name__)


def create_operation_log(context, checkpoint, operation_type=None):
    checkpoint_dict = checkpoint.to_dict()
    extra_info = checkpoint_dict.get('extra_info', None)
    scheduled_operation_id = None
    if extra_info:
        extra_info_dict = jsonutils.loads(extra_info)
        created_by = extra_info_dict.get('created_by', None)
        if created_by == constants.OPERATION_ENGINE:
            scheduled_operation_id = extra_info_dict.get(
                'scheduled_operation_id', None)

    protection_plan = checkpoint_dict['protection_plan']
    plan_id = None
    provider_id = None
    if protection_plan:
        plan_id = protection_plan.get("id")
        provider_id = protection_plan.get("provider_id")
    operation_log_properties = {
        'project_id': checkpoint_dict['project_id'],
        'operation_type': (
            constants.OPERATION_PROTECT if operation_type is None
            else operation_type),
        'checkpoint_id': checkpoint_dict['id'],
        'plan_id': plan_id,
        'provider_id': provider_id,
        'scheduled_operation_id': scheduled_operation_id,
        'status': checkpoint_dict['status'],
        'started_at': timeutils.utcnow()
    }
    try:
        operation_log = objects.OperationLog(context=context,
                                             **operation_log_properties)
        operation_log.create()
        return operation_log
    except Exception:
        LOG.error('Error creating operation log. checkpoint: %s',
                  checkpoint.id)
        raise


def update_operation_log(context, operation_log, fields):
    if not isinstance(operation_log, objects_base.KarborObject):
        msg = _("The parameter must be a object of "
                "KarborObject class.")
        raise exception.InvalidInput(reason=msg)

    try:
        operation_log.update(fields)
        operation_log.save()
    except Exception:
        LOG.error('Error update operation log. operation_log: %s',
                  operation_log.id)
        raise


def create_operation_log_restore(context, restore):
    operation_log_properties = {
        'project_id': restore.get('project_id'),
        'operation_type': constants.OPERATION_RESTORE,
        'checkpoint_id': restore.get('checkpoint_id'),
        'plan_id': restore.get('plan_id', None),
        'provider_id': restore.get('provider_id'),
        'restore_id': restore.get('id'),
        'status': restore.get('status'),
        'started_at': timeutils.utcnow()
    }
    try:
        operation_log = objects.OperationLog(context=context,
                                             **operation_log_properties)
        operation_log.create()
        return operation_log
    except Exception:
        LOG.error('Error creating operation log. checkpoint: %s',
                  restore.id)
        raise


def create_operation_log_verify(context, verify):
    operation_log_properties = {
        'project_id': verify.get('project_id'),
        'operation_type': constants.OPERATION_VERIFY,
        'checkpoint_id': verify.get('checkpoint_id'),
        'plan_id': verify.get('plan_id', None),
        'provider_id': verify.get('provider_id'),
        'status': verify.get('status'),
        'started_at': timeutils.utcnow()
    }
    try:
        operation_log = objects.OperationLog(context=context,
                                             **operation_log_properties)
        operation_log.create()
        return operation_log
    except Exception:
        LOG.error('Error creating operation log. verify: %s',
                  verify.id)
        raise
