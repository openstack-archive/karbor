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

OPTIONS_SCHEMA = {
    "title": "Volume Snapshot Options",
    "type": "object",
    "properties": {
        "snapshot_name": {
            "type": "string",
            "title": "Snapshot Name",
            "description": "The name of the snapshot.",
            "default": None
        },
        "description": {
            "type": "string",
            "title": "Description",
            "description": "The description of the volume."
        },
        "force": {
            "type": "boolean",
            "title": "Force",
            "description": "Allows or disallows snapshot of a volume when the"
                           "volume is attached to an instance.",
            "default": False
        }
    },
    "required": ["snapshot_name", "force"]
}

RESTORE_SCHEMA = {
    "title": "Volume snapshot Restore",
    "type": "object",
    "properties": {
        "restore_name": {
            "type": "string",
            "title": "Restore Volume Name",
            "description": "The name of the restore volume",
            "default": None
        },
        "restore_description": {
            "type": "string",
            "title": "Restore Description",
            "description": "The description of the restored volume.",
            "default": None
        }
    },
    "required": ["restore_name"]
}

SAVED_INFO_SCHEMA = {
    "title": "Volume Protection Saved Info",
    "type": "object",
    "properties": {},
    "required": []
}
