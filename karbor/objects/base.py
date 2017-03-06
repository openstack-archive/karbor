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

"""karbor common internal object model"""

import contextlib
import datetime

from oslo_log import log as logging
from oslo_versionedobjects import base
from oslo_versionedobjects import fields

from karbor import db
from karbor.db.sqlalchemy import models
from karbor import exception
from karbor.i18n import _
from karbor import objects


LOG = logging.getLogger('object')
remotable = base.remotable
remotable_classmethod = base.remotable_classmethod
obj_make_list = base.obj_make_list


class KarborObjectRegistry(base.VersionedObjectRegistry):
    def registration_hook(self, cls, index):
        setattr(objects, cls.obj_name(), cls)
        # For Versioned Object Classes that have a model store the model in
        # a Class attribute named model
        try:
            model_name = cls.obj_name()
            cls.model = getattr(models, model_name)
        except (ImportError, AttributeError):
            pass


class KarborObject(base.VersionedObject):
    OBJ_SERIAL_NAMESPACE = 'karbor_object'
    OBJ_PROJECT_NAMESPACE = 'karbor'

    def karbor_obj_get_changes(self):
        """Returns a dict of changed fields with tz unaware datetimes.

        Any timezone aware datetime field will be converted to UTC timezone
        and returned as timezone unaware datetime.

        This will allow us to pass these fields directly to a db update
        method as they can't have timezone information.
        """
        # Get dirtied/changed fields
        changes = self.obj_get_changes()

        # Look for datetime objects that contain timezone information
        for k, v in changes.items():
            if isinstance(v, datetime.datetime) and v.tzinfo:
                # Remove timezone information and adjust the time according to
                # the timezone information's offset.
                changes[k] = v.replace(tzinfo=None) - v.utcoffset()

        # Return modified dict
        return changes

    @base.remotable_classmethod
    def get_by_id(cls, context, id, *args, **kwargs):
        # To get by id we need to have a model and for the model to
        # have an id field
        if 'id' not in cls.fields:
            msg = (_('VersionedObject %s cannot retrieve object by id.') %
                   (cls.obj_name()))
            raise NotImplementedError(msg)

        model = getattr(models, cls.obj_name())
        orm_obj = db.get_by_id(context, model, id, *args, **kwargs)
        kargs = {}
        if hasattr(cls, 'DEFAULT_EXPECTED_ATTR'):
            kargs = {'expected_attrs': getattr(cls, 'DEFAULT_EXPECTED_ATTR')}
        return cls._from_db_object(context, cls(context), orm_obj, **kargs)

    def refresh(self):
        # To refresh we need to have a model and for the model to have an id
        # field
        if 'id' not in self.fields:
            msg = (_('VersionedObject %s cannot retrieve object by id.') %
                   (self.obj_name()))
            raise NotImplementedError(msg)

        current = self.get_by_id(self._context, self.id)

        for field in self.fields:
            # Only update attributes that are already set.  We do not want to
            # unexpectedly trigger a lazy-load.
            if self.obj_attr_is_set(field):
                if self[field] != current[field]:
                    self[field] = current[field]
        self.obj_reset_changes()

    def __contains__(self, name):
        # We're using obj_extra_fields to provide aliases for some fields while
        # in transition period. This override is to make these aliases pass
        # "'foo' in obj" tests.
        return name in self.obj_extra_fields or super(KarborObject,
                                                      self).__contains__(name)


class KarborObjectDictCompat(base.VersionedObjectDictCompat):
    """Mix-in to provide dictionary key access compat.

    If an object needs to support attribute access using
    dictionary items instead of object attributes, inherit
    from this class. This should only be used as a temporary
    measure until all callers are converted to use modern
    attribute access.

    NOTE(berrange) This class will eventually be deleted.
    """

    def get(self, key, value=base._NotSpecifiedSentinel):
        """For backwards-compatibility with dict-based objects.

        NOTE(danms): May be removed in the future.
        """
        if key not in self.obj_fields:
            # NOTE(jdg): There are a number of places where we rely on the
            # old dictionary version and do a get(xxx, None).
            # The following preserves that compatibility but in
            # the future we'll remove this shim altogether so don't
            # rely on it.
            LOG.debug('Karbor object %(object_name)s has no '
                      'attribute named: %(attribute_name)s',
                      {'object_name': self.__class__.__name__,
                       'attribute_name': key})
            return None
        if (value != base._NotSpecifiedSentinel and
                not self.obj_attr_is_set(key)):
            return value
        else:
            try:
                return getattr(self, key)
            except (exception.ObjectActionError, NotImplementedError):
                # Exception when haven't set a value for non-lazy
                # loadable attribute, but to mimic typical dict 'get'
                # behavior we should still return None
                return None


def DateTimeField(**kwargs):
    return fields.DateTimeField(tzinfo_aware=False, **kwargs)


class KarborPersistentObject(object):
    """Mixin class for Persistent objects.

    This adds the fields that we use in common for all persistent objects.
    """
    fields = {
        'created_at': DateTimeField(nullable=True),
        'updated_at': DateTimeField(nullable=True),
        'deleted_at': DateTimeField(nullable=True),
        'deleted': fields.BooleanField(default=False),
    }

    @contextlib.contextmanager
    def obj_as_admin(self):
        """Context manager to make an object call as an admin.

        This temporarily modifies the context embedded in an object to
        be elevated() and restores it after the call completes. Example
        usage:

           with obj.obj_as_admin():
               obj.save()
        """
        if self._context is None:
            raise exception.OrphanedObjectError(method='obj_as_admin',
                                                objtype=self.obj_name())

        original_context = self._context
        self._context = self._context.elevated()
        try:
            yield
        finally:
            self._context = original_context


class KarborComparableObject(base.ComparableVersionedObject):
    def __eq__(self, obj):
        if hasattr(obj, 'obj_to_primitive'):
            return self.obj_to_primitive() == obj.obj_to_primitive()
        return False


class ObjectListBase(base.ObjectListBase):
    pass


class KarborObjectSerializer(base.VersionedObjectSerializer):
    OBJ_BASE_CLASS = KarborObject


class DictOfDictOfStringsField(fields.AutoTypedField):
    AUTO_TYPE = fields.Dict(fields.Dict(fields.String(), nullable=True))
