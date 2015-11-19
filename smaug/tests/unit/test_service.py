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
Unit Tests for remote procedure calls using queue
"""

import mock
from oslo_concurrency import processutils
from oslo_config import cfg

from smaug import exception
from smaug import service
from smaug.tests import base
from smaug.wsgi import common as wsgi


CONF = cfg.CONF


class TestWSGIService(base.TestCase):

    def setUp(self):
        super(TestWSGIService, self).setUp()

    @mock.patch('smaug.utils.find_config')
    def test_service_random_port(self, mock_find_config):
        with mock.patch.object(wsgi.Loader, 'load_app') as mock_load_app:
            test_service = service.WSGIService("test_service")
            self.assertEqual(0, test_service.port)
            test_service.start()
            self.assertNotEqual(0, test_service.port)
            test_service.stop()
            self.assertTrue(mock_load_app.called)

    @mock.patch('smaug.utils.find_config')
    def test_reset_pool_size_to_default(self, mock_find_config):
        with mock.patch.object(wsgi.Loader, 'load_app') as mock_load_app:
            test_service = service.WSGIService("test_service")
            test_service.start()

            # Stopping the service, which in turn sets pool size to 0
            test_service.stop()
            self.assertEqual(0, test_service.server._pool.size)

            # Resetting pool size to default
            test_service.reset()
            test_service.start()
            self.assertEqual(1000, test_service.server._pool.size)
            self.assertTrue(mock_load_app.called)

    @mock.patch('smaug.utils.find_config')
    @mock.patch('smaug.wsgi.common.Loader.load_app')
    @mock.patch('smaug.wsgi.eventlet_server.Server')
    def test_workers_set_default(self, wsgi_server, mock_load_app,
                                 mock_find_config):
        test_service = service.WSGIService("osapi_smaug")
        self.assertEqual(processutils.get_worker_count(), test_service.workers)

    @mock.patch('smaug.utils.find_config')
    @mock.patch('smaug.wsgi.common.Loader.load_app')
    @mock.patch('smaug.wsgi.eventlet_server.Server')
    def test_workers_set_good_user_setting(self, wsgi_server,
                                           mock_load_app,
                                           mock_find_config):
        self.override_config('osapi_smaug_workers', 8)
        test_service = service.WSGIService("osapi_smaug")
        self.assertEqual(8, test_service.workers)

    @mock.patch('smaug.utils.find_config')
    @mock.patch('smaug.wsgi.common.Loader.load_app')
    @mock.patch('smaug.wsgi.eventlet_server.Server')
    def test_workers_set_zero_user_setting(self, wsgi_server,
                                           mock_load_app,
                                           mock_find_config):
        self.override_config('osapi_smaug_workers', 0)
        test_service = service.WSGIService("osapi_smaug")
        # If a value less than 1 is used, defaults to number of procs available
        self.assertEqual(processutils.get_worker_count(), test_service.workers)

    @mock.patch('smaug.utils.find_config')
    @mock.patch('smaug.wsgi.common.Loader.load_app')
    @mock.patch('smaug.wsgi.eventlet_server.Server')
    def test_workers_set_negative_user_setting(self, wsgi_server,
                                               mock_load_app,
                                               mock_find_config):
        self.override_config('osapi_smaug_workers', -1)
        self.assertRaises(exception.InvalidInput,
                          service.WSGIService,
                          "osapi_smaug")
        self.assertFalse(wsgi_server.called)
