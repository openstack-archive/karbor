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

"""
Operation classes
"""

from karbor import loadables
from karbor.services.operationengine.operations import base


class OperationHandler(loadables.BaseLoader):

    def __init__(self):
        super(OperationHandler, self).__init__(base.Operation)


def all_operations():
    """Get all operation classes."""
    return OperationHandler().get_all_classes()
