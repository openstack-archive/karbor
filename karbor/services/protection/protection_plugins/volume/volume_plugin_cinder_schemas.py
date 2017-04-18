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
    "title": "Cinder Protection Options",
    "type": "object",
    "properties": {
        "backup_name": {
            "type": "string",
            "title": "Backup Name",
            "description": "The name of the backup.",
            "default": None
        },
        "backup_mode": {
            "type": "string",
            "title": "Backup Mode",
            "description": "The backup mode.",
            "enum": ["full", "incremental"],
            "default": "full"
        },
        "container": {
            "type": "string",
            "title": "Container",
            "description": "The container which been chosen.",
            "default": None
        },
        "description": {
            "type": "string",
            "title": "Description",
            "description": "The description of the volume.",
            "default": None
        },
        "force": {
            "type": "boolean",
            "title": "Force",
            "description": "Whether to backup, even if the volume"
                           "is attached",
            "default": False
        }
    },
    "required": ["backup_name", "backup_mode", "container", "force"]
}

RESTORE_SCHEMA = {
    "title": "Cinder Protection Restore",
    "type": "object",
    "properties": {
        "volume_id": {
            "type": "string",
            "title": "Volume ID",
            "description": "The target volume ID to restore to.",
            "default": None
        },
        "restore_name": {
            "type": "string",
            "title": "Restore Name",
            "description": "The name of the restored volume.",
            "default": None
        },
        "restore_description": {
            "type": "string",
            "title": "Restore Description",
            "description": "The description of the restored volume.",
            "default": None
        }
    }
}

SAVED_INFO_SCHEMA = {
    "title": "Cinder Protection Saved Info",
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "title": "Name",
            "description": "The name for this backup."
        },
        "is_incremental": {
            "type": "boolean",
            "title": "Is Incremental",
            "description":
                "The type of the backup, "
                "True is incremental and False is full."
        },
        "status": {
            "type": "string",
            "title": "Status",
            "description": "The backup status, such as available.",
            "enum": ['creating', 'available',
                                 'deleting', 'error',
                                 'restoring', 'error_restoring'],
        },
        "progress": {
            "type": "number",
            "title": "Progress",
            "description":
            "The current operation progress for this backup.",
            "constraint": {'min': 0, 'max': 1},
        },
        "fail_reason": {
            "type": "string",
            "title": "Fail Reason",
            "description":
                "The reason for the failure status of the backup."
        },
        "size": {
            "type": "integer",
            "title": "Size",
            "description": "The size of the backup, in GB."
        },
        "volume_id": {
            "type": "string",
            "title": "Volume ID",
            "description":
                ("The ID of the volume "
                 "from which the backup was created.")
        },
    },
    "required": ["name", "status", "progress", "fail_reason",
                 "size", "volume_id"]
}
