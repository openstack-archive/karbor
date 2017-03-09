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

"""Handles all requests relating to protection service."""


from karbor.db import base
from karbor.services.protection import rpcapi as protection_rpcapi


class API(base.Base):
    """API for interacting with the protection manager."""

    def __init__(self, db_driver=None):
        self.protection_rpcapi = protection_rpcapi.ProtectionAPI()
        super(API, self).__init__(db_driver)

    def restore(self, context, restore, restore_auth):
        return self.protection_rpcapi.restore(context, restore, restore_auth)

    def protect(self, context, plan, checkpoint_properties):
        return self.protection_rpcapi.protect(context, plan,
                                              checkpoint_properties)

    def delete(self, context, provider_id, checkpoint_id):
        return self.protection_rpcapi.delete(
            context,
            provider_id,
            checkpoint_id
        )

    def show_checkpoint(self, context, provider_id, checkpoint_id):
        return self.protection_rpcapi.show_checkpoint(
            context,
            provider_id,
            checkpoint_id
        )

    def list_checkpoints(self, context, provider_id, marker, limit,
                         sort_keys, sort_dirs, filters, offset):
        return self.protection_rpcapi.list_checkpoints(
            context,
            provider_id,
            marker,
            limit,
            sort_keys,
            sort_dirs,
            filters
        )

    def list_protectable_types(self, context):
        return self.protection_rpcapi.list_protectable_types(context)

    def show_protectable_type(self, context, protectable_type):
        return self.protection_rpcapi.show_protectable_type(
            context,
            protectable_type
        )

    def list_protectable_instances(self, context, protectable_type,
                                   marker, limit, sort_keys,
                                   sort_dirs, filters, offset, parameters):
        return self.protection_rpcapi.list_protectable_instances(
            context,
            protectable_type,
            marker,
            limit,
            sort_keys,
            sort_dirs,
            filters,
            parameters
        )

    def list_protectable_dependents(self, context,
                                    protectable_id,
                                    protectable_type):
        return self.protection_rpcapi.list_protectable_dependents(
            context,
            protectable_id,
            protectable_type
        )

    def show_protectable_instance(self, context,
                                  protectable_type,
                                  protectable_id,
                                  parameters=None):
        return self.protection_rpcapi.show_protectable_instance(
            context,
            protectable_type,
            protectable_id,
            parameters=parameters
        )

    def show_provider(self, context, provider_id):
        return self.protection_rpcapi.show_provider(context, provider_id)

    def list_providers(self, context, marker, limit,
                       sort_keys, sort_dirs, filters, offset):
        return self.protection_rpcapi.list_providers(
            context,
            marker,
            limit,
            sort_keys,
            sort_dirs,
            filters
        )
