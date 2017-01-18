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

"""Base Manager class.

Managers are responsible for a certain aspect of the system.  It is a logical
grouping of code relating to a portion of the system.  In general other
components should be using the manager to make changes to the components that
it is responsible for.

We have adopted a basic strategy of Smart managers and dumb data, which means
rather than attaching methods to data objects, components should call manager
methods that act on the data.

Methods on managers that can be executed locally should be called directly. If
a particular method must execute on a remote host, this should be done via rpc
to the service that wraps the manager

Managers should be responsible for most of the db access, and
non-implementation specific data.  Anything implementation specific that can't
be generalized should be done by the Driver.

Managers will often provide methods for initial setup of a host or periodic
tasks to a wrapping service.

This module provides Manager, a base class for managers.

"""


from oslo_config import cfg
import oslo_messaging as messaging
from oslo_service import periodic_task

from karbor.db import base
from karbor import version


CONF = cfg.CONF


class PeriodicTasks(periodic_task.PeriodicTasks):
    def __init__(self):
        super(PeriodicTasks, self).__init__(CONF)


class Manager(base.Base, PeriodicTasks):
    # Set RPC API version to 1.0 by default.
    RPC_API_VERSION = '1.0'

    target = messaging.Target(version=RPC_API_VERSION)

    def __init__(self, host=None, db_driver=None):
        if not host:
            host = CONF.host
        self.host = host
        self.additional_endpoints = []
        super(Manager, self).__init__(db_driver)

    def periodic_tasks(self, context, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        return self.run_periodic_tasks(context, raise_on_error=raise_on_error)

    def init_host(self, **kwargs):
        """Handle initialization if this is a standalone service.

        A hook point for services to execute tasks before the services are made
        available (i.e. showing up on RPC and starting to accept RPC calls) to
        other components.  Child classes should override this method.

        """
        pass

    def cleanup_host(self):
        """Hook to do cleanup work when the service shuts down.

        Child classes should override this method.
        """
        pass

    def init_host_with_rpc(self):
        """A hook for service to do jobs after RPC is ready.

        Like init_host(), this method is a hook where services get a chance
        to execute tasks that *need* RPC. Child classes should override
        this method.

        """
        pass

    def service_version(self):
        return version.version_string()

    def service_config(self):
        config = {}
        for key in CONF:
            config[key] = CONF.get(key, None)
        return config

    def is_working(self):
        """Method indicating if service is working correctly.

        This method is supposed to be overridden by subclasses and return if
        manager is working correctly.
        """
        return True
