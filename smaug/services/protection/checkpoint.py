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
from oslo_utils import uuidutils
from smaug.services.protection import graph

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

_INDEX_FILE_NAME = "index.json"
_UUID_STR_LEN = 36


class Checkpoint(object):
    VERSION = "0.9"
    SUPPORTED_VERSIONS = ["0.9"]

    def __init__(self, checkpoint_section, bank_lease, checkpoint_id):
        self._id = checkpoint_id
        self._checkpoint_section = checkpoint_section
        self._bank_lease = bank_lease
        self.reload_meta_data()

    @property
    def bank_section(self):
        return self._bank_section

    @property
    def id(self):
        return self._id

    @property
    def status(self):
        # TODO(saggi): check for valid values and transitions
        return self._md_cache["status"]

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
            # Something bad happend invalidate the object
            self._md_cache = None
            self._checkpoint_section = None
            raise RuntimeError(
                "Checkpoint was created in an unsupported version")

    def reload_meta_data(self):
        new_md = self._checkpoint_section.get_object(_INDEX_FILE_NAME)
        self._assert_supported_version(new_md)
        self._md_cache = new_md

    @classmethod
    def _generate_id(self):
        return uuidutils.generate_uuid()

    @classmethod
    def get_by_section(cls, bank_section, bank_lease, checkpoint_id):
        # TODO(yuvalbr) add validation that the checkpoint exists
        checkpoint_section = bank_section.get_sub_section(checkpoint_id)
        return Checkpoint(checkpoint_section, bank_lease, checkpoint_id)

    @classmethod
    def create_in_section(cls, bank_section, bank_lease, owner_id,
                          plan, checkpoint_id=None):
        checkpoint_id = checkpoint_id or cls._generate_id()
        checkpoint_section = bank_section.get_sub_section(checkpoint_id)
        checkpoint_section.create_object(
            key=_INDEX_FILE_NAME,
            value={
                "version": cls.VERSION,
                "id": checkpoint_id,
                "status": "protecting",
                "owner_id": owner_id,
                "protection_plan": {
                    "id": plan.get("id"),
                    "name": plan.get("name"),
                    "resources": plan.get("resources")
                }
            }
        )
        return Checkpoint(checkpoint_section,
                          bank_lease,
                          checkpoint_id)

    def commit(self):
        self._checkpoint_section.create_object(
            key=_INDEX_FILE_NAME,
            value=self._md_cache,
        )

    def purge(self):
        """Purge the index file of the checkpoint.

        Can only be done if the checkpoint has no other files apart from the
        index.
        """
        all_objects = self._checkpoint_section.list_objects(prefix=self.id)
        if (
            len(all_objects) == 1
            and all_objects[0] == _INDEX_FILE_NAME
        ) or len(all_objects) == 0:
            self._checkpoint_section.delete_object(_INDEX_FILE_NAME)
        else:
            raise RuntimeError("Could not delete: Checkpoint is not empty")

    def get_resource_bank_section(self, resource_id):
        prefix = "/resource-data/%s/%s/" % (self._id, resource_id)
        return self._checkpoint_section.get_sub_section(prefix)


class CheckpointCollection(object):

    def __init__(self, bank, bank_lease=None):
        super(CheckpointCollection, self).__init__()
        self._bank = bank
        self._bank_lease = bank_lease
        self._checkpoints_section = bank.get_sub_section("/checkpoints")

    def list_ids(self, limit=None, marker=None):
        checkpoint_ids = {key[:_UUID_STR_LEN]
                          for key in self._checkpoints_section.list_objects(
                              limit=limit,
                              marker=marker)
                          }

        return [checkpoint_id for checkpoint_id in checkpoint_ids
                if uuidutils.is_uuid_like(checkpoint_id)
                ]

    def get(self, checkpoint_id):
        # TODO(saggi): handle multiple instances of the same checkpoint
        return Checkpoint.get_by_section(self._checkpoints_section,
                                         self._bank_lease,
                                         checkpoint_id)

    def create(self, plan):
        # TODO(saggi): Serialize plan to checkpoint. Will be done in
        # future patches.
        return Checkpoint.create_in_section(self._checkpoints_section,
                                            self._bank_lease,
                                            self._bank.get_owner_id(),
                                            plan)
