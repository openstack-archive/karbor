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
    "title": "Volume Glance Protection Options",
    "type": "object",
    "properties": {
        "backup_name": {
            "type": "string",
            "title": "Backup Name",
            "description": "The name of the backup.",
            "default": None
        },
        "description": {
            "type": "string",
            "title": "Description",
            "description": "The description of the backup."
        }
    },
    "required": ["backup_name"]
}

RESTORE_SCHEMA = {
    "title": "Volume Glance Protection Restore",
    "type": "object",
    "properties": {
        "restore_name": {
            "type": "string",
            "title": "Restore Resource Name",
            "description": "The name of the restore resource ",
            "default": None
        },
    },
    "required": ["restore_name"]
}

VERIFY_SCHEMA = {
    "title": "Volume Glance Protection Verify",
    "type": "object",
    "properties": {}
}

SAVED_INFO_SCHEMA = {
    "title": "Volume Glance Protection Saved Info",
    "type": "object",
    "properties": {},
    "required": []
}
