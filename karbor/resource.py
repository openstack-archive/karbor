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


class Resource(object):
    __slots__ = ('type', 'id', 'name', 'extra_info')

    def __init__(self, type, id, name, extra_info=None):
        self.type = type
        self.id = id
        self.name = name
        self.extra_info = extra_info

    def __setattr__(self, key, value):
        try:
            getattr(self, key)
        except AttributeError:
            pass
        else:
            raise AttributeError()

        return super(Resource, self).__setattr__(key, value)

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return self.key == other.key

    def to_dict(self):
        return {item: getattr(self, item) for item in self.__slots__}

    @property
    def key(self):
        return (self.type, self.id, self.name)
