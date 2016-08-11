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

import sys

try:
    from unittest import mock
except ImportError:
    import mock
from oslo_config import cfg

from karbor.cmd import api as karbor_api
from karbor.tests import base
from karbor import version

CONF = cfg.CONF


class TestKarborApiCmd(base.TestCase):
    """Unit test cases for python modules under karbor/cmd."""

    def setUp(self):
        super(TestKarborApiCmd, self).setUp()
        sys.argv = ['karbor-api']
        CONF(sys.argv[1:], project='karbor', version=version.version_string())

    def tearDown(self):
        super(TestKarborApiCmd, self).tearDown()

    @mock.patch('karbor.service.WSGIService')
    @mock.patch('karbor.service.process_launcher')
    @mock.patch('karbor.rpc.init')
    @mock.patch('oslo_log.log.setup')
    def test_main(self, log_setup, rpc_init, process_launcher,
                  wsgi_service):
        launcher = process_launcher.return_value
        server = wsgi_service.return_value
        server.workers = mock.sentinel.worker_count

        karbor_api.main()

        self.assertEqual('karbor', CONF.project)
        self.assertEqual(CONF.version, version.version_string())
        log_setup.assert_called_once_with(CONF, "karbor")
        rpc_init.assert_called_once_with(CONF)
        process_launcher.assert_called_once_with()
        wsgi_service.assert_called_once_with('osapi_karbor')
        launcher.launch_service.assert_called_once_with(server,
                                                        workers=server.workers)
        launcher.wait.assert_called_once_with()
