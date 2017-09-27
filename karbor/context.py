# Copyright 2011 OpenStack Foundation
#
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

"""RequestContext: context for requests that persist through all of karbor."""

import copy

from oslo_config import cfg
from oslo_context import context
from oslo_utils import timeutils
import six

from karbor import exception
from karbor.i18n import _
from karbor.objects import base as objects_base
from karbor import policy

CONF = cfg.CONF


class RequestContext(context.RequestContext):
    """Security context and request information.

    Represents the user taking a given action within the system.

    """
    def __init__(self, user_id, project_id, is_admin=None, read_deleted="no",
                 roles=None, project_name=None, remote_address=None,
                 timestamp=None, request_id=None, auth_token=None,
                 overwrite=True, quota_class=None, service_catalog=None,
                 domain=None, user_domain=None, project_domain=None,
                 auth_token_info=None):
        """Initialize RequestContext.

        :param read_deleted: 'no' indicates deleted records are hidden, 'yes'
            indicates deleted records are visible, 'only' indicates that
            *only* deleted records are visible.

        :param overwrite: Set to False to ensure that the greenthread local
            copy of the index is not overwritten.
        """

        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=user_id,
                                             tenant=project_id,
                                             domain=domain,
                                             user_domain=user_domain,
                                             project_domain=project_domain,
                                             is_admin=is_admin,
                                             request_id=request_id)
        self.roles = roles or []
        self.project_name = project_name
        self.read_deleted = read_deleted
        self.remote_address = remote_address
        if not timestamp:
            timestamp = timeutils.utcnow()
        elif isinstance(timestamp, six.string_types):
            timestamp = timeutils.parse_isotime(timestamp)
        self.timestamp = timestamp
        self.quota_class = quota_class
        self._auth_token_info = auth_token_info

        if service_catalog:
            # Only include required parts of service_catalog
            self.service_catalog = [s for s in service_catalog
                                    if s.get('type') in
                                    ('identity', 'compute', 'object-store',
                                     'image', 'volume', 'volumev2', 'network',
                                     'volumev3', 'orchestration',
                                     'share', 'sharev2', 'database')]
        else:
            # if list is empty or none
            self.service_catalog = []

        # We need to have RequestContext attributes defined
        # when policy.check_is_admin invokes request logging
        # to make it loggable.
        if self.is_admin is None:
            self.is_admin = policy.check_is_admin(self)
        elif self.is_admin and 'admin' not in self.roles:
            self.roles.append('admin')

    def _get_read_deleted(self):
        return self._read_deleted

    def _set_read_deleted(self, read_deleted):
        if read_deleted not in ('no', 'yes', 'only'):
            raise ValueError(_("read_deleted can only be one of 'no', "
                               "'yes' or 'only', not %r") % read_deleted)
        self._read_deleted = read_deleted

    def _del_read_deleted(self):
        del self._read_deleted

    read_deleted = property(_get_read_deleted, _set_read_deleted,
                            _del_read_deleted)

    def to_dict(self):
        result = super(RequestContext, self).to_dict()
        result['user_id'] = self.user_id
        result['project_id'] = self.project_id
        result['project_name'] = self.project_name
        result['domain'] = self.domain
        result['read_deleted'] = self.read_deleted
        result['roles'] = self.roles
        result['remote_address'] = self.remote_address
        result['timestamp'] = self.timestamp.isoformat()
        result['quota_class'] = self.quota_class
        result['service_catalog'] = self.service_catalog
        result['request_id'] = self.request_id
        result['auth_token_info'] = self._auth_token_info
        return result

    @classmethod
    def from_dict(cls, values):
        allowed_keys = [
            'user_id',
            'project_id',
            'project_name',
            'domain',
            'read_deleted',
            'remote_address',
            'timestamp',
            'quota_class',
            'service_catalog',
            'request_id',
            'is_admin',
            'roles',
            'auth_token',
            'user_domain',
            'project_domain',
            'auth_token_info'
        ]
        kwargs = {k: values[k] for k in values if k in allowed_keys}
        return cls(**kwargs)

    def can(self, action, target_obj=None, fatal=True):
        """Verifies that the given action is valid on the target in this context.

        :param action: string representing the action to be checked.
        :param target: dictionary representing the object of the action
            for object creation this should be a dictionary representing the
            location of the object e.g. ``{'project_id': context.project_id}``.
            If None, then this default target will be considered:
            {'project_id': self.project_id, 'user_id': self.user_id}
        :param: target_obj: dictionary representing the object which will be
            used to update target.
        :param fatal: if False, will return False when an
            exception.NotAuthorized occurs.

        :raises nova.exception.Forbidden: if verification fails and fatal is
            True.

        :return: returns a non-False value (not necessarily "True") if
            authorized and False if not authorized and fatal is False.
        """
        target = {'project_id': self.project_id,
                  'user_id': self.user_id}
        if isinstance(target_obj, objects_base.KarborObject):
            # Turn object into dict so target.update can work
            target.update(
                target_obj.obj_to_primitive()['karbor_object.data'] or {})
        else:
            target.update(target_obj or {})

        try:
            return policy.authorize(self, action, target)
        except exception.NotAuthorized:
            if fatal:
                raise
            return False

    def to_policy_values(self):
        policy = super(RequestContext, self).to_policy_values()

        policy['is_admin'] = self.is_admin

        return policy

    def elevated(self, read_deleted=None, overwrite=False):
        """Return a version of this context with admin flag set."""
        context = self.deepcopy()
        context.is_admin = True

        if 'admin' not in context.roles:
            context.roles.append('admin')

        if read_deleted is not None:
            context.read_deleted = read_deleted

        return context

    def deepcopy(self):
        return copy.deepcopy(self)

    @property
    def project_id(self):
        return self.tenant

    @project_id.setter
    def project_id(self, value):
        self.tenant = value

    @property
    def user_id(self):
        return self.user

    @user_id.setter
    def user_id(self, value):
        self.user = value

    @property
    def auth_token_info(self):
        return self._auth_token_info


def get_admin_context(read_deleted="no"):
    return RequestContext(user_id=None,
                          project_id=None,
                          is_admin=True,
                          read_deleted=read_deleted,
                          overwrite=False)
