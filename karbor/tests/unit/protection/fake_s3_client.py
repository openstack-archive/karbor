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

from botocore.exceptions import ClientError


class FakeS3Client(object):
    def __init__(self, *args, **kwargs):
        super(FakeS3Client, self).__init__()

    @classmethod
    def connection(cls, *args, **kargs):
        return FakeS3Connection()


class FakeS3Connection(object):
    def __init__(self, *args, **kwargs):
        super(FakeS3Connection, self).__init__()
        self.s3_dir = {}
        self.object_headers = {}

    def create_bucket(self, Bucket):
        self.s3_dir[Bucket] = {
            'Keys': {}
        }

    def list_objects(self, Bucket, Prefix, Marker):
        body = []
        prefix = '' if not Prefix else Prefix
        for obj in self.s3_dir[Bucket]['Keys'].keys():
            if obj.startswith(prefix):
                body.append({
                    'Key': obj
                })
        if len(body) == 0:
            return {
                'IsTruncated': False
            }
        else:
            return {
                'Contents': body,
                'IsTruncated': False
            }

    def put_object(self, Bucket, Key, Body, Metadata=None):
        if Bucket in self.s3_dir.keys():
            self.s3_dir[Bucket]['Keys'][Key] = {
                'Body': FakeS3Stream(Body),
                'Metadata': Metadata if Metadata else {}
            }
        else:
            raise ClientError("error_bucket")

    def get_object(self, Bucket, Key):
        if Bucket in self.s3_dir.keys():
            if Key in self.s3_dir[Bucket]['Keys'].keys():
                return self.s3_dir[Bucket]['Keys'][Key]
            else:
                raise ClientError("error_object")
        else:
            raise ClientError("error_bucket")

    def delete_object(self, Bucket, Key):
        if Bucket in self.s3_dir.keys():
            if Key in self.s3_dir[Bucket]['Keys'].keys():
                del self.s3_dir[Bucket]['Keys'][Key]
            else:
                raise ClientError("error_object")
        else:
            raise ClientError("error_bucket")


class FakeS3Stream(object):
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data
