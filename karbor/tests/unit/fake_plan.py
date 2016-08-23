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

db_plan = {
    'id': '1',
    'name': 'My 3 tier application',
    'provider_id': 'efc6a88b-9096-4bb6-8634-cda182a6e12a',
    'status': 'started',
    'project_id': '39bb894794b741e982bd26144d2949f6',
    'resources': [],
    'parameters': '{"OS::Nova::Server": {"consistency": "os"}}',
}


def fake_db_plan(**updates):
    for name, field in objects.Plan.fields.items():
        if name in db_plan:
            continue
        if field.nullable:
            db_plan[name] = None
        elif field.default != fields.UnspecifiedDefault:
            db_plan[name] = field.default
        else:
            raise Exception('fake_db_plan needs help with %s.' % name)

    if updates:
        db_plan.update(updates)

    return db_plan
