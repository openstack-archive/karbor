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

import logging
import os

import fixtures
from oslo_config import cfg
from oslo_messaging import conffixture as messaging_conffixture
from oslo_utils import timeutils
from oslotest import base

from karbor.common import config  # noqa Need to register global_opts
from karbor.db import migration
from karbor.db.sqlalchemy import api as sqla_api
from karbor import rpc
from karbor.tests.unit import conf_fixture


CONF = cfg.CONF

_DB_CACHE = None


class Database(fixtures.Fixture):

    def __init__(self, db_api, db_migrate, sql_connection):
        super(Database, self).__init__()
        self.sql_connection = sql_connection

        # Suppress logging for test runs
        migrate_logger = logging.getLogger('migrate')
        migrate_logger.setLevel(logging.WARNING)

        self.engine = db_api.get_engine()
        self.engine.dispose()
        conn = self.engine.connect()
        db_migrate.db_sync()

        self._DB = "".join(line for line in conn.connection.iterdump())
        self.engine.dispose()

    def setUp(self):
        super(Database, self).setUp()

        conn = self.engine.connect()
        conn.connection.executescript(self._DB)
        self.addCleanup(self.engine.dispose)


class TestCase(base.BaseTestCase):

    """Test case base class for all unit tests."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCase, self).setUp()

        rpc.add_extra_exmods("karbor.tests.unit")
        self.addCleanup(rpc.clear_extra_exmods)
        self.addCleanup(rpc.cleanup)

        self.messaging_conf = messaging_conffixture.ConfFixture(CONF)
        self.messaging_conf.transport_driver = 'fake'
        self.messaging_conf.response_timeout = 15
        self.useFixture(self.messaging_conf)
        rpc.init(CONF)

        conf_fixture.set_defaults(CONF)
        CONF([], default_config_files=[])

        # NOTE(vish): We need a better method for creating fixtures for tests
        #             now that we have some required db setup for the system
        #             to work properly.
        self.start = timeutils.utcnow()

        CONF.set_default('connection', 'sqlite://', 'database')
        CONF.set_default('sqlite_synchronous', False, 'database')

        global _DB_CACHE
        if not _DB_CACHE:
            _DB_CACHE = Database(sqla_api, migration,
                                 sql_connection=CONF.database.connection)
        self.useFixture(_DB_CACHE)

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
