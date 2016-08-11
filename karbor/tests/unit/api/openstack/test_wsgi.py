# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from karbor.api.openstack import wsgi
from karbor.tests import base


class RequestTest(base.TestCase):
    def test_content_type_missing(self):
        request = wsgi.Request.blank('/tests/123', method='POST')
        request.body = b"<body />"
        self.assertIsNone(request.get_content_type())

    def test_content_type_unsupported(self):
        request = wsgi.Request.blank('/tests/123', method='POST')
        request.headers["Content-Type"] = "text/html"
        request.body = b"asdf<br />"
        self.assertIsNone(request.get_content_type())

    def test_content_type_with_charset(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Content-Type"] = "application/json; charset=UTF-8"
        result = request.get_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_accept(self):
        for content_type in ('application/json',):
            request = wsgi.Request.blank('/tests/123')
            request.headers["Accept"] = content_type
            result = request.best_match_content_type()
            self.assertEqual(content_type, result)

    def test_content_type_from_accept_best(self):
        request = wsgi.Request.blank('/tests/123')
        request.headers["Accept"] = "application/xml, application/json"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_from_query_extension(self):
        request = wsgi.Request.blank('/tests/123.json')
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

        request = wsgi.Request.blank('/tests/123.invalid')
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)

    def test_content_type_accept_default(self):
        request = wsgi.Request.blank('/tests/123.unsupported')
        request.headers["Accept"] = "application/unsupported1"
        result = request.best_match_content_type()
        self.assertEqual("application/json", result)


class ActionDispatcherTest(base.TestCase):
    def test_dispatch(self):
        serializer = wsgi.ActionDispatcher()
        serializer.create = lambda x: 'pants'
        self.assertEqual('pants', serializer.dispatch({}, action='create'))

    def test_dispatch_action_none(self):
        serializer = wsgi.ActionDispatcher()
        serializer.create = lambda x: 'pants'
        serializer.default = lambda x: 'trousers'
        self.assertEqual('trousers', serializer.dispatch({}, action=None))

    def test_dispatch_default(self):
        serializer = wsgi.ActionDispatcher()
        serializer.create = lambda x: 'pants'
        serializer.default = lambda x: 'trousers'
        self.assertEqual('trousers', serializer.dispatch({}, action='update'))


class DictSerializerTest(base.TestCase):
    def test_dispatch_default(self):
        serializer = wsgi.DictSerializer()
        self.assertEqual('', serializer.serialize({}, 'update'))


class JSONDictSerializerTest(base.TestCase):
    def test_json(self):
        input_dict = dict(servers=dict(a=(2, 3)))
        expected_json = '{"servers":{"a":[2,3]}}'
        serializer = wsgi.JSONDictSerializer()
        result = serializer.serialize(input_dict)
        result = result.replace('\n', '').replace(' ', '')
        self.assertEqual(expected_json, result)


class TextDeserializerTest(base.TestCase):
    def test_dispatch_default(self):
        deserializer = wsgi.TextDeserializer()
        self.assertEqual({}, deserializer.deserialize({}, 'update'))


class JSONDeserializerTest(base.TestCase):
    def test_json(self):
        data = """{"a": {
                "a1": "1",
                "a2": "2",
                "bs": ["1", "2", "3", {"c": {"c1": "1"}}],
                "d": {"e": "1"},
                "f": "1"}}"""
        as_dict = {
            'body': {
                'a': {
                    'a1': '1',
                    'a2': '2',
                    'bs': ['1', '2', '3', {'c': {'c1': '1'}}],
                    'd': {'e': '1'},
                    'f': '1',
                },
            },
        }
        deserializer = wsgi.JSONDeserializer()
        self.assertEqual(as_dict, deserializer.deserialize(data))
