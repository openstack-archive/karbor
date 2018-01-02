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

import copy
import itertools

import karbor.api.common
import karbor.api.v1.protectables
import karbor.api.v1.providers
import karbor.common.config
import karbor.db.api
import karbor.exception
import karbor.service
import karbor.services.operationengine.engine.executors.green_thread_executor as green_thread_executor  # noqa
import karbor.services.operationengine.engine.executors.thread_pool_executor as thread_pool_executor  # noqa
import karbor.services.operationengine.engine.triggers.timetrigger as time_trigger  # noqa
import karbor.services.operationengine.karbor_client
import karbor.services.operationengine.manager
import karbor.services.operationengine.operations.base as base
import karbor.services.protection.clients.cinder
import karbor.services.protection.clients.glance
import karbor.services.protection.clients.manila
import karbor.services.protection.clients.neutron
import karbor.services.protection.clients.nova
import karbor.services.protection.flows.restore
import karbor.services.protection.flows.worker
import karbor.services.protection.manager
import karbor.wsgi.eventlet_server

__all__ = ['list_opts']

_opts = [
    ('clients_keystone', list(itertools.chain(
        karbor.common.config.keystone_client_opts))),
    ('operationengine', list(itertools.chain(
        green_thread_executor.green_thread_executor_opts,
        karbor.services.operationengine.manager.trigger_manager_opts))),
    ('karbor_client', list(itertools.chain(
        karbor.common.config.service_client_opts))),
    ('cinder_client', list(itertools.chain(
        karbor.common.config.service_client_opts,
        karbor.services.protection.clients.cinder.cinder_client_opts))),
    ('glance_client', list(itertools.chain(
        karbor.common.config.service_client_opts,
        karbor.services.protection.clients.glance.glance_client_opts))),
    ('manila_client', list(itertools.chain(
        karbor.common.config.service_client_opts,
        karbor.services.protection.clients.manila.manila_client_opts))),
    ('neutron_client', list(itertools.chain(
        karbor.common.config.service_client_opts,
        karbor.services.protection.clients.neutron.neutron_client_opts))),
    ('nova_client', list(itertools.chain(
        karbor.common.config.service_client_opts,
        karbor.services.protection.clients.nova.nova_client_opts))),
    ('DEFAULT', list(itertools.chain(
        karbor.common.config.core_opts,
        karbor.common.config.debug_opts,
        karbor.common.config.global_opts,
        karbor.api.common.api_common_opts,
        karbor.api.v1.protectables.query_instance_filters_opts,
        karbor.api.v1.providers.query_provider_filters_opts,
        karbor.api.v1.providers.query_checkpoint_filters_opts,
        karbor.db.api.db_opts,
        thread_pool_executor.executor_opts,
        time_trigger.time_trigger_opts,
        base.record_operation_log_executor_opts,
        karbor.services.protection.flows.restore.sync_status_opts,
        karbor.services.protection.flows.worker.workflow_opts,
        karbor.services.protection.manager.protection_manager_opts,
        karbor.wsgi.eventlet_server.socket_opts,
        karbor.exception.exc_log_opts,
        karbor.service.service_opts)))]


def list_opts():
    return [(g, copy.deepcopy(o)) for g, o in _opts]
