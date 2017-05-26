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

"""karbor base exception handling.

Includes decorator for re-raising karbor-type exceptions.

SHOULD include dedicated exception logging.

"""

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_versionedobjects import exception as obj_exc
import six
import webob.exc
from webob.util import status_generic_reasons
from webob.util import status_reasons

from six.moves import http_client

from karbor.i18n import _


LOG = logging.getLogger(__name__)

exc_log_opts = [
    cfg.BoolOpt('fatal_exception_format_errors',
                default=False,
                help='Make exception message format errors fatal.'),
]

CONF = cfg.CONF
CONF.register_opts(exc_log_opts)


class ConvertedException(webob.exc.WSGIHTTPException):
    def __init__(self, code=500, title="",
                 explanation=""):
        self.code = code
        # There is a strict rule about constructing status line for HTTP:
        # '...Status-Line, consisting of the protocol version followed by a
        # numeric status code and its associated textual phrase, with each
        # element separated by SP characters'
        # (http://www.faqs.org/rfcs/rfc2616.html)
        # 'code' and 'title' can not be empty because they correspond
        # to numeric status code and its associated text
        if title:
            self.title = title
        else:
            try:
                self.title = status_reasons[self.code]
            except KeyError:
                generic_code = self.code // 100
                self.title = status_generic_reasons[generic_code]
        self.explanation = explanation
        super(ConvertedException, self).__init__()


class Error(Exception):
    pass


class KarborException(Exception):
    """Base karbor Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = _("An unknown exception occurred.")
    code = http_client.INTERNAL_SERVER_ERROR
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        """Initiate the instance of KarborException

        There are two ways to initiate the instance.
        1. Specify the value of 'message' and leave the 'kwargs' None.
        2. Leave 'message' None, and specify the keyword arguments matched
           with the format of KarborException.message. Especially, can't
           use the 'message' as the key in the 'kwargs', otherwise, the
           first argument('message') will be set.

        Note: This class doesn't support to create instance of KarborException
            with another instance.
        """
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error("%(name)s: %(value)s",
                              {'name': name, 'value': value})
                if CONF.fatal_exception_format_errors:
                    six.reraise(*exc_info)
                # at least get the core message out if something happened
                message = self.message
        elif isinstance(message, Exception):
            message = six.text_type(message)

        # NOTE(luisg): We put the actual message in 'msg' so that we can access
        # it, because if we try to access the message via 'message' it will be
        # overshadowed by the class' message attribute
        self.msg = message
        super(KarborException, self).__init__(message)

    def __unicode__(self):
        return six.text_type(self.msg)


class NotAuthorized(KarborException):
    message = _("Not authorized.")
    code = http_client.FORBIDDEN


class AdminRequired(NotAuthorized):
    message = _("User does not have admin privileges")


class PolicyNotAuthorized(NotAuthorized):
    message = _("Policy doesn't allow %(action)s to be performed.")


class AuthorizationFailure(NotAuthorized):
    message = _("Authorization for %(obj)s is failed ")


class Invalid(KarborException):
    message = _("Unacceptable parameters.")
    code = http_client.BAD_REQUEST


class InvalidParameterValue(Invalid):
    message = _("%(err)s")


class InvalidInput(Invalid):
    message = _("Invalid input received: %(reason)s")


class ScheduledOperationExist(Invalid):
    message = _("Scheduled Operation%(op_id)s exists")


class NotFound(KarborException):
    message = _("Resource could not be found.")
    code = http_client.NOT_FOUND
    safe = True


class ConfigNotFound(NotFound):
    message = _("Could not find config at %(path)s")


class MalformedRequestBody(KarborException):
    message = _("Malformed message body: %(reason)s")


class InvalidContentType(Invalid):
    message = _("Invalid content type %(content_type)s.")


class InvalidProtectableInstance(Invalid):
    message = _("Invalid protectable instance.")


class PasteAppNotFound(NotFound):
    message = _("Could not load paste app '%(name)s' from %(path)s")


class ServiceNotFound(NotFound):
    message = _("Service %(service_id)s could not be found.")


class HostBinaryNotFound(NotFound):
    message = _("Could not find binary %(binary)s on host %(host)s.")


class TriggerNotFound(NotFound):
    message = _("Trigger %(id)s could not be found.")


class ScheduledOperationNotFound(NotFound):
    message = _("Scheduled Operation %(id)s could not be found.")


class ScheduledOperationStateNotFound(NotFound):
    message = _("Scheduled Operation State %(op_id)s could not be found.")


class ScheduledOperationLogNotFound(NotFound):
    message = _("Scheduled Operation Log %(log_id)s could not be found.")


class ListProtectableResourceFailed(KarborException):
    message = _("List protectable resources of type %(type)s failed: "
                "%(reason)s")


class ProtectableResourceNotFound(NotFound):
    message = _("The resource %(id)s of type %(type)s could not be found: "
                "%(reason)s")


class ProtectableResourceInvalidStatus(KarborException):
    message = _("The resource %(id)s of type %(type)s has a invalid "
                "status: %(status)s")


class InvalidOperationObject(Invalid):
    message = _("The operation %(operation_id)s is invalid")


class DeleteTriggerNotAllowed(NotAuthorized):
    message = _("Can not delete trigger %(trigger_id)s")


class ClassNotFound(NotFound):
    message = _("Class %(class_name)s could not be found: %(exception)s")


class InvalidOperationDefinition(Invalid):
    message = _("Invalid operation definition, reason:%(reason)s")


OrphanedObjectError = obj_exc.OrphanedObjectError
ObjectActionError = obj_exc.ObjectActionError


class PlanNotFound(NotFound):
    message = _("Plan %(plan_id)s could not be found.")


class RestoreNotFound(NotFound):
    message = _("Restore %(restore_id)s could not be found.")


class OperationLogNotFound(NotFound):
    message = _("OperationLog %(restore_id)s could not be found.")


class InvalidPlan(Invalid):
    message = _("Invalid plan: %(reason)s")


class ProtectableTypeNotFound(NotFound):
    message = _("ProtectableType %(protectable_type)s could"
                " not be found.")


class ProtectionPluginNotFound(NotFound):
    message = _("Protection Plugin for %(type)s could"
                " not be found.")


class ProviderNotFound(NotFound):
    message = _("Provider %(provider_id)s could"
                " not be found.")


class CheckpointRecordNotFound(NotFound):
    message = _("CheckpointRecord %(id)s could not be found.")


class CreateBackupFailed(KarborException):
    message = _("Create Backup failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class CreateResourceFailed(KarborException):
    message = _("Create %(name)s failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class DeleteResourceFailed(KarborException):
    message = _("Delete %(name)s failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class RestoreResourceFailed(KarborException):
    message = _("Restore %(name)s failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class DeleteBackupFailed(KarborException):
    message = _("Delete Backup failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class RestoreBackupFailed(KarborException):
    message = _("Restore Backup failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class GetBackupFailed(KarborException):
    message = _("Get Backup failed: %(reason)s, id=%(resource_id)s,"
                " type=%(resource_type)s")


class FlowError(KarborException):
    message = _("Flow: %(flow)s, Error: %(error)s")


class CheckpointNotFound(NotFound):
    message = _("Checkpoint %(checkpoint_id)s could"
                " not be found.")


class BankCreateObjectFailed(KarborException):
    message = _("Create Object in Bank Failed: %(reason)s")


class BankUpdateObjectFailed(KarborException):
    message = _("Update Object %(key)s in Bank Failed: %(reason)s")


class BankDeleteObjectFailed(KarborException):
    message = _("Delete Object %(key)s in Bank Failed: %(reason)s")


class BankGetObjectFailed(KarborException):
    message = _("Get Object %(key)s in Bank Failed: %(reason)s")


class BankListObjectsFailed(KarborException):
    message = _("Get Object in Bank Failed: %(reason)s")


class BankReadonlyViolation(KarborException):
    message = _("Bank read-only violation")


class AcquireLeaseFailed(KarborException):
    message = _("Acquire Lease in Failed: %(reason)s")


class CreateContainerFailed(KarborException):
    message = _("Create Container in Bank Failed: %(reason)s")


class TriggerIsInvalid(Invalid):
    message = _("Trigger%(trigger_id)s is invalid.")


class InvalidTaskFlowObject(Invalid):
    message = _("The task flow is invalid: %(reason)s")


class InvalidOriginalId(Invalid):
    message = _("The original_id: %(original_id)s is invalid.")


class CheckpointNotAvailable(KarborException):
    message = _("The checkpoint %(checkpoint_id)s is not available")


class CheckpointNotBeDeleted(KarborException):
    message = _("The checkpoint %(checkpoint_id)s can not be deleted.")
