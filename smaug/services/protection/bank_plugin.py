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


from oslo_config import cfg
from oslo_log import log as logging

import abc
import six

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BankPlugin(object):
    @abc.abstractmethod
    def create_object(self, key, value):
        return

    @abc.abstractmethod
    def update_object(self, key, options, value):
        return

    @abc.abstractmethod
    def get_object(self, key):
        return

    @abc.abstractmethod
    def list_objects(self, options):
        return

    @abc.abstractmethod
    def delete_object(self, key):
        return

    @abc.abstractmethod
    def chroot(self, context):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def show_object(self, key):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def acquire_lease(self, owner_id):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def renew_lease(self, owner_id):
        # TODO(wangliuan)
        pass

    @abc.abstractmethod
    def check_lease_validity(self):
        # TODO(wangliuan)
        pass
