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

"""Unit tests for `karbor.wsgi`."""

import mock

from oslo_config import cfg
import testtools

from karbor.tests import base
from karbor.wsgi import eventlet_server as wsgi

CONF = cfg.CONF


class WSGIServerTest(base.TestCase):
    """WSGI server tests."""
    def _ipv6_configured():
        try:
            with open('/proc/net/if_inet6') as f:
                return len(f.read()) > 0
        except IOError:
            return False

    def test_no_app(self):
        server = wsgi.Server("test_app", None,
                             host="127.0.0.1", port=0)
        self.assertEqual("test_app", server.name)

    def test_start_random_port(self):
        server = wsgi.Server("test_random_port", None, host="127.0.0.1")
        server.start()
        self.assertNotEqual(0, server.port)
        server.stop()
        server.wait()

    @testtools.skipIf(not _ipv6_configured(),
                      "Test requires an IPV6 configured interface")
    def test_start_random_port_with_ipv6(self):
        server = wsgi.Server("test_random_port",
                             None,
                             host="::1")
        server.start()
        self.assertEqual("::1", server.host)
        self.assertNotEqual(0, server.port)
        server.stop()
        server.wait()

    def test_server_pool_waitall(self):
        # test pools waitall method gets called while stopping server
        server = wsgi.Server("test_server", None,
                             host="127.0.0.1")
        server.start()
        with mock.patch.object(server._pool,
                               'waitall') as mock_waitall:
            server.stop()
            server.wait()
            mock_waitall.assert_called_once_with()

    def test_reset_pool_size_to_default(self):
        server = wsgi.Server("test_resize", None, host="127.0.0.1")
        server.start()

        # Stopping the server, which in turn sets pool size to 0
        server.stop()
        self.assertEqual(0, server._pool.size)

        # Resetting pool size to default
        server.reset()
        server.start()
        self.assertEqual(1000, server._pool.size)
