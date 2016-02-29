# Copyright 2010 OpenStack Foundation
# All Rights Reserved.
#
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


def fake_protection_plan():
    protection_plan = {'id': 'fake_id',
                       'is_enabled': True,
                       'name': 'fake_protection_plan',
                       'comments': '',
                       'revision': 0,
                       'resources': [],
                       'protection_provider': None,
                       'parameters': {},
                       'provider_id': 'fake_id'
                       }
    return protection_plan


def fake_protection_definitions():
    protection_definitions = [{'plugin_id': 'fake_plugin_id'}]
    return protection_definitions


class FakeCheckpointManager(object):
    def __init__(self):
        super(FakeCheckpointManager, self).__init__()
        self.fake_checkpoint = None
        self.fake_checkpoint_status = None
        self.fake_protection_definition = None

    def list_checkpoints(self, list_options):
        # TODO(wangliuan)
        pass

    def show_checkpoint(self, checkpoint_id):
        return 'fake_checkpoint'

    def delete_checkpoint(self, checkpoint_id):
        # TODO(wangliuan)
        pass

    def create_checkpoint(self, plan):
        self.fake_checkpoint = 'fake_checkpoint'
        return 'fake_checkpoint'

    def update_checkpoint(self, checkpoint, **kwargs):
        status = kwargs.get('status', 'error')
        self.fake_checkpoint_status = status

    def update_protection_definition(self, checkpoint, **kwargs):
        self.fake_protection_definition = 'fake_definition'


class FakeProtectablePlugin(object):
    def get_resource_type(self):
        pass

    def get_parent_resource_types(self):
        pass

    def list_resources(self):
        pass

    def get_dependent_resources(self, parent_resource):
        pass
