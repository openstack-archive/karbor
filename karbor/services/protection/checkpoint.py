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

from datetime import datetime
from karbor.common import constants
from karbor import exception
from karbor.i18n import _
from karbor.services.protection import graph
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import timeutils
from oslo_utils import uuidutils

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

_INDEX_FILE_NAME = "index.json"
_UUID_STR_LEN = 36


class Checkpoint(object):
    VERSION = "0.9"
    SUPPORTED_VERSIONS = ["0.9"]

    def __init__(self, checkpoint_section, indices_section,
                 bank_lease, checkpoint_id):
        super(Checkpoint, self).__init__()
        self._id = checkpoint_id
        self._checkpoint_section = checkpoint_section
        self._indices_section = indices_section
        self._bank_lease = bank_lease
        self.reload_meta_data()

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status,
            "protection_plan": self.protection_plan,
            "extra_info": self._md_cache.get("extra_info", None),
            "project_id": self.project_id,
            "resource_graph": self._md_cache.get("resource_graph", None),
            "created_at": self._md_cache.get("created_at", None)
        }

    @property
    def checkpoint_section(self):
        return self._checkpoint_section

    @property
    def id(self):
        return self._id

    @property
    def provider_id(self):
        return self._md_cache["provider_id"]

    @property
    def created_at(self):
        return self._md_cache["created_at"]

    @property
    def status(self):
        # TODO(saggi): check for valid values and transitions
        return self._md_cache["status"]

    @property
    def project_id(self):
        return self._md_cache["project_id"]

    @property
    def owner_id(self):
        # TODO(yinwei): check for valid values and transitions
        return self._md_cache["owner_id"]

    @property
    def resource_graph(self):
        serialized_resource_graph = self._md_cache.get("resource_graph", None)
        if serialized_resource_graph is not None:
            resource_graph = graph.deserialize_resource_graph(
                serialized_resource_graph)
            return resource_graph
        else:
            return None

    @property
    def protection_plan(self):
        return self._md_cache["protection_plan"]

    @status.setter
    def status(self, value):
        self._md_cache["status"] = value

    @resource_graph.setter
    def resource_graph(self, resource_graph):
        serialized_resource_graph = graph.serialize_resource_graph(
            resource_graph)
        self._md_cache["resource_graph"] = serialized_resource_graph

    def _is_supported_version(self, version):
        return version in self.SUPPORTED_VERSIONS

    def _assert_supported_version(self, new_md):
        if new_md["version"] not in self.SUPPORTED_VERSIONS:
            # Something bad happened invalidate the object
            self._md_cache = None
            self._checkpoint_section = None
            raise RuntimeError(
                _("Checkpoint was created in an unsupported version"))

    def reload_meta_data(self):
        try:
            new_md = self._checkpoint_section.get_object(_INDEX_FILE_NAME)
        except exception.BankGetObjectFailed:
            LOG.error("unable to reload metadata for checkpoint id: %s",
                      self.id)
            raise exception.CheckpointNotFound(checkpoint_id=self.id)
        self._assert_supported_version(new_md)
        self._md_cache = new_md

    @classmethod
    def _generate_id(self):
        return uuidutils.generate_uuid()

    @classmethod
    def get_by_section(cls, checkpoints_section, indices_section,
                       bank_lease, checkpoint_id):
        # TODO(yuvalbr) add validation that the checkpoint exists
        checkpoint_section = checkpoints_section.get_sub_section(checkpoint_id)
        return Checkpoint(checkpoint_section, indices_section,
                          bank_lease, checkpoint_id)

    @classmethod
    def create_in_section(cls, checkpoints_section, indices_section,
                          bank_lease, owner_id, plan,
                          checkpoint_id=None, checkpoint_properties=None):
        checkpoint_id = checkpoint_id or cls._generate_id()
        checkpoint_section = checkpoints_section.get_sub_section(checkpoint_id)

        timestamp = timeutils.utcnow_ts()
        created_at = timeutils.utcnow().strftime('%Y-%m-%d')

        provider_id = plan.get("provider_id")
        extra_info = None
        if checkpoint_properties:
            extra_info = checkpoint_properties.get("extra_info", None)
        checkpoint_section.update_object(
            key=_INDEX_FILE_NAME,
            value={
                "version": cls.VERSION,
                "id": checkpoint_id,
                "status": constants.CHECKPOINT_STATUS_PROTECTING,
                "owner_id": owner_id,
                "provider_id": provider_id,
                "project_id": plan.get("project_id"),
                "protection_plan": {
                    "id": plan.get("id"),
                    "name": plan.get("name"),
                    "provider_id": plan.get("provider_id"),
                    "resources": plan.get("resources")
                },
                "extra_info": extra_info,
                "created_at": created_at,
                "timestamp": timestamp
            }
        )

        indices_section.update_object(
            key="/by-provider/%s/%s@%s" % (provider_id, timestamp,
                                           checkpoint_id),
            value=checkpoint_id
        )

        indices_section.update_object(
            key="/by-date/%s/%s@%s" % (created_at, timestamp, checkpoint_id),
            value=checkpoint_id
        )

        indices_section.update_object(
            key="/by-plan/%s/%s/%s@%s" % (
                plan.get("id"), created_at, timestamp, checkpoint_id),
            value=checkpoint_id)

        return Checkpoint(checkpoint_section,
                          indices_section,
                          bank_lease,
                          checkpoint_id)

    def commit(self):
        self._checkpoint_section.update_object(
            key=_INDEX_FILE_NAME,
            value=self._md_cache,
        )

    def purge(self):
        """Purge the index file of the checkpoint.

        Can only be done if the checkpoint has no other files apart from the
        index.
        """
        all_objects = self._checkpoint_section.list_objects()
        if len(all_objects) == 1 and all_objects[0] == _INDEX_FILE_NAME:
            created_at = self._md_cache["created_at"]
            timestamp = self._md_cache["timestamp"]
            plan_id = self._md_cache["protection_plan"]["id"]
            provider_id = self._md_cache["protection_plan"]["provider_id"]
            self._indices_section.delete_object(
                "/by-provider/%s/%s@%s" % (provider_id, timestamp, self.id))
            self._indices_section.delete_object(
                "/by-date/%s/%s@%s" % (created_at, timestamp, self.id))
            self._indices_section.delete_object(
                "/by-plan/%s/%s/%s@%s" % (
                    plan_id, created_at, timestamp, self.id))

            self._checkpoint_section.delete_object(_INDEX_FILE_NAME)
        else:
            raise RuntimeError(_("Could not delete: Checkpoint is not empty"))

    def delete(self):
        self.status = constants.CHECKPOINT_STATUS_DELETED
        self.commit()
        # delete indices
        created_at = self._md_cache["created_at"]
        timestamp = self._md_cache["timestamp"]
        plan_id = self._md_cache["protection_plan"]["id"]
        provider_id = self._md_cache["protection_plan"]["provider_id"]
        self._indices_section.delete_object(
            "/by-provider/%s/%s@%s" % (provider_id, timestamp, self.id))
        self._indices_section.delete_object(
            "/by-date/%s/%s@%s" % (created_at, timestamp, self.id))
        self._indices_section.delete_object(
            "/by-plan/%s/%s/%s@%s" % (
                plan_id, created_at, timestamp, self.id))

    def get_resource_bank_section(self, resource_id):
        prefix = "/resource-data/%s/" % resource_id
        return self._checkpoint_section.get_sub_section(prefix)


class CheckpointCollection(object):

    def __init__(self, bank, bank_lease=None):
        super(CheckpointCollection, self).__init__()
        self._bank = bank
        self._bank_lease = bank_lease
        self._checkpoints_section = bank.get_sub_section("/checkpoints")
        self._indices_section = bank.get_sub_section("/indices")

    def list_ids(self, provider_id, limit=None, marker=None, plan_id=None,
                 start_date=None, end_date=None, sort_dir=None):
        marker_checkpoint = None
        if marker is not None:
            checkpoint_section = self._checkpoints_section.get_sub_section(
                marker)
            marker_checkpoint = checkpoint_section.get_object(_INDEX_FILE_NAME)
            timestamp = marker_checkpoint["timestamp"]
            marker = "%s@%s" % (timestamp, marker)

        if start_date is not None:
            if end_date is None:
                end_date = timeutils.utcnow()

        if plan_id is None and start_date is None:
            prefix = "/by-provider/%s/" % provider_id
            if marker is not None:
                marker = "/%s" % marker
        elif plan_id is not None:
            prefix = "/by-plan/%s/" % plan_id
            if marker is not None:
                date = marker_checkpoint["created_at"]
                marker = "/by-plan/%s/%s/%s" % (plan_id, date, marker)
        else:
            prefix = "/by-date/"
            if marker is not None:
                date = marker_checkpoint["created_at"]
                marker = "/by-date/%s/%s" % (date, marker)

        return self._list_ids(prefix, limit, marker, start_date, end_date,
                              sort_dir)

    def _list_ids(self, prefix, limit, marker, start_date, end_date, sort_dir):
        if start_date is None:
            return [key[key.find("@") + 1:]
                    for key in self._indices_section.list_objects(
                    prefix=prefix,
                    limit=limit,
                    marker=marker,
                    sort_dir=sort_dir
                    )]
        else:
            ids = []
            for key in self._indices_section.list_objects(prefix=prefix,
                                                          marker=marker,
                                                          sort_dir=sort_dir):
                date = datetime.strptime(key.split("/")[-2], "%Y-%m-%d")
                if start_date <= date <= end_date:
                    ids.append(key[key.find("@") + 1:])
                if limit is not None and len(ids) == limit:
                    return ids
            return ids

    def get(self, checkpoint_id):
        # TODO(saggi): handle multiple instances of the same checkpoint
        return Checkpoint.get_by_section(self._checkpoints_section,
                                         self._indices_section,
                                         self._bank_lease,
                                         checkpoint_id)

    def create(self, plan, checkpoint_properties=None):
        # TODO(saggi): Serialize plan to checkpoint. Will be done in
        # future patches.
        return Checkpoint.create_in_section(
            self._checkpoints_section,
            self._indices_section,
            self._bank_lease,
            self._bank.get_owner_id(),
            plan,
            checkpoint_properties=checkpoint_properties)
