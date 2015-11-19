# -*- coding: utf-8 -*-

# Copyright 2010-2011 OpenStack Foundation
#
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
import os

from oslo_config import cfg
from oslo_log import log
from oslotest import base

from smaug.common import config  # noqa Need to register global_opts
from smaug.tests.unit import conf_fixture

test_opts = [

]

CONF = cfg.CONF
CONF.register_opts(test_opts)

LOG = log.getLogger(__name__)


class TestCase(base.BaseTestCase):

    """Test case base class for all unit tests."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCase, self).setUp()

        conf_fixture.set_defaults(CONF)
        CONF([], default_config_files=[])

        self.override_config('policy_file',
                             os.path.join(
                                 os.path.abspath(
                                     os.path.join(
                                         os.path.dirname(__file__),
                                         '..',
                                     )
                                 ),
                                 'tests/unit/policy.json'),
                             group='oslo_policy')

    def override_config(self, name, override, group=None):
        """Cleanly override CONF variables."""
        CONF.set_override(name, override, group)
        self.addCleanup(CONF.clear_override, name, group)

    def flags(self, **kw):
        """Override CONF variables for a test."""
        for k, v in kw.items():
            self.override_config(k, v)
