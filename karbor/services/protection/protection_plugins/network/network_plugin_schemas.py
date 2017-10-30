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
    "title": "Network Protection Options",
    "type": "object",
    "properties": {},
    "required": []
}

RESTORE_SCHEMA = {
    "title": "Network Protection Restore",
    "type": "object",
    "properties": {
        "restore_name": {
            "type": "string",
            "title": "Restore Network Name",
            "description": "The name of the restore network",
        },
    },
    "required": ["restore_name"]
}

VERIFY_SCHEMA = {
    "title": "Network Protection Verify",
    "type": "object",
    "properties": {}
}

SAVED_INFO_SCHEMA = {
    "title": "Network Protection Saved Info",
    "type": "object",
    "properties": {},
    "required": []
}
