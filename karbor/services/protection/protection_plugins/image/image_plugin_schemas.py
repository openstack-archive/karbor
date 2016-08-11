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
    "title": "Image Protection Options",
    "type": "object",
    "properties": {
        "backup_name": {
            "type": "string",
            "title": "Backup Name",
            "description": "The name of the backup.",
            "default": None
        }
    },
    "required": []
}

RESTORE_SCHEMA = {
    "title": "Image Protection Restore",
    "type": "object",
    "properties": {
        "restore_name": {
            "type": "string",
            "title": "Restore Image Name",
            "description": "The name of the restore image",
        },
    },
    "required": ["backup_name"]
}

# TODO(hurong)
SAVED_INFO_SCHEMA = {
    "title": "Image Protection Saved Info",
    "type": "object",
    "properties": {
        "image_metadata": {
            "type": "image",
            "title": "Image Metadata",
            "description": "To save disk_format and container_format",
        }
    },
    "required": ["image_metadata"]
}
