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
Test WSGI basics and provide some helper functions for other WSGI tests.
"""

import mock
import six
import tempfile

import routes
import webob

from karbor.tests import base
from karbor.wsgi import common as wsgi_common


class CommonTest(base.TestCase):

    def test_debug(self):

        class Application(wsgi_common.Application):
            """Dummy application to test debug."""

            def __call__(self, environ, start_response):
                start_response("200", [("X-Test", "checking")])
                return [b'Test result']

        with mock.patch('sys.stdout', new=six.StringIO()) as mock_stdout:
            mock_stdout.buffer = six.BytesIO()
            application = wsgi_common.Debug(Application())
            result = webob.Request.blank('/').get_response(application)
            self.assertEqual(b"Test result", result.body)

    def test_router(self):

        class Application(wsgi_common.Application):
            """Test application to call from router."""

            def __call__(self, environ, start_response):
                start_response("200", [])
                return [b'Router result']

        class Router(wsgi_common.Router):
            """Test router."""

            def __init__(self):
                mapper = routes.Mapper()
                mapper.connect("/test", controller=Application())
                super(Router, self).__init__(mapper)

        result = webob.Request.blank('/test').get_response(Router())
        self.assertEqual(b"Router result", result.body)
        result = webob.Request.blank('/bad').get_response(Router())
        self.assertNotEqual(b"Router result", result.body)


class LoaderNormalFilesystemTest(base.TestCase):
    """Loader tests with normal filesystem (unmodified os.path module)."""

    _paste_config = """
[app:test_app]
use = egg:Paste#static
document_root = /tmp
    """

    def setUp(self):
        super(LoaderNormalFilesystemTest, self).setUp()
        self.config = tempfile.NamedTemporaryFile(mode="w+t")
        self.config.write(self._paste_config.lstrip())
        self.config.seek(0)
        self.config.flush()
        self.loader = wsgi_common.Loader(self.config.name)
        self.addCleanup(self.config.close)

    def test_config_found(self):
        self.assertEqual(self.config.name, self.loader.config_path)

    def test_app_found(self):
        url_parser = self.loader.load_app("test_app")
        self.assertEqual("/tmp", url_parser.directory)
