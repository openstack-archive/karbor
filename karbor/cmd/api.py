#!/usr/bin/env python
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Starter script for karbor OS API."""

import eventlet
eventlet.monkey_patch()

import sys  # noqa: E402

from oslo_config import cfg  # noqa: E402
from oslo_log import log as logging  # noqa: E402

# Need to register global_opts
from karbor.common import config  # noqa
from karbor import i18n  # noqa: E402
i18n.enable_lazy()
from karbor import objects  # noqa: E402
from karbor import rpc  # noqa: E402
from karbor import service  # noqa: E402
from karbor import version  # noqa: E402


CONF = cfg.CONF


def main():
    objects.register_all()
    CONF(sys.argv[1:], project='karbor',
         version=version.version_string())
    logging.setup(CONF, "karbor")

    rpc.init(CONF)
    launcher = service.get_launcher()
    server = service.WSGIService('osapi_karbor')
    launcher.launch_service(server, workers=server.workers)
    launcher.wait()
