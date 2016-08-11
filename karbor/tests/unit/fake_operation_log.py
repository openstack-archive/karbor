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

from oslo_versionedobjects import fields

from karbor import objects


def fake_db_operation_log(**updates):
    db_operation_log = {
        "id": "36ea41b2-c358-48a7-9117-70cb7617410a",
        "project_id": "586cc6ce-e286-40bd-b2b5-dd32694d9944",
        "scheduled_operation_id": "2220f8b1-975d-4621-a872-fa9afb43cb6c",
        "state": "failed",
        "error": "Could not access bank",
        "entries": "[entries:{'timestamp': '2015-08-27T09:50:51-05:00',"
                   "'message': 'Doing things'}]"
    }
    for name, field in objects.OperationLog.fields.items():
        if name in db_operation_log:
            continue
        if field.nullable:
            db_operation_log[name] = None
        elif field.default != fields.UnspecifiedDefault:
            db_operation_log[name] = field.default
        else:
            raise Exception('db_operation_log needs help with %s.' % name)

    if updates:
        db_operation_log.update(updates)

    return db_operation_log
