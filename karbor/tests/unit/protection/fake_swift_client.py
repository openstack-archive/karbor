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

import os
import tempfile

from swiftclient import ClientException


class FakeSwiftClient(object):
    def __init__(self, *args, **kwargs):
        super(FakeSwiftClient, self).__init__()

    @classmethod
    def connection(cls, *args, **kargs):
        return FakeSwiftConnection()


class FakeSwiftConnection(object):
    def __init__(self, *args, **kwargs):
        super(FakeSwiftConnection, self).__init__()
        self.swiftdir = tempfile.mkdtemp()
        self.object_headers = {}

    def put_container(self, container):
        container_dir = self.swiftdir + "/" + container
        if os.path.exists(container_dir) is True:
            return
        else:
            os.makedirs(container_dir)

    def get_container(self, container, prefix, limit, marker, end_marker):
        container_dir = self.swiftdir + "/" + container
        body = []
        if prefix:
            objects_dir = container_dir + "/" + prefix
        else:
            objects_dir = container_dir
        for f in os.listdir(objects_dir):
            if os.path.isfile(objects_dir + "/" + f):
                body.append({"name": f})
            else:
                body.append({"subdir": f})
        return None, body

    def put_object(self, container, obj, contents, headers=None):
        container_dir = self.swiftdir + "/" + container
        obj_file = container_dir + "/" + obj
        obj_dir = obj_file[0:obj_file.rfind("/")]
        if os.path.exists(container_dir) is True:
            if os.path.exists(obj_dir) is False:
                os.makedirs(obj_dir)
            with open(obj_file, "w") as f:
                f.write(contents)

            self.object_headers[obj_file] = {}
            for key, value in headers.items():
                self.object_headers[obj_file][str(key)] = str(value)
            return
        else:
            raise ClientException("error_container")

    def get_object(self, container, obj):
        container_dir = self.swiftdir + "/" + container
        obj_file = container_dir + "/" + obj
        if os.path.exists(container_dir) is True:
            if os.path.exists(obj_file) is True:
                with open(obj_file, "r") as f:
                    return self.object_headers[obj_file], f.read()
            else:
                raise ClientException("error_obj")
        else:
            raise ClientException("error_container")

    def delete_object(self, container, obj):
        container_dir = self.swiftdir + "/" + container
        obj_file = container_dir + "/" + obj
        if os.path.exists(container_dir) is True:
            if os.path.exists(obj_file) is True:
                os.remove(obj_file)
                self.object_headers.pop(obj_file)
            else:
                raise ClientException("error_obj")
        else:
            raise ClientException("error_container")
