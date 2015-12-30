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
import shutil

import fixtures
from oslo_config import cfg
from oslo_log import log
from oslotest import base

from smaug.common import config  # noqa Need to register global_opts
from smaug.db import migration
from smaug.db.sqlalchemy import api as sqla_api
from smaug.tests.unit import conf_fixture

test_opts = [
    cfg.StrOpt('sqlite_clean_db',
               default='clean.sqlite',
               help='File name of clean sqlite db'), ]

CONF = cfg.CONF
CONF.register_opts(test_opts)

LOG = log.getLogger(__name__)

_DB_CACHE = None


class Database(fixtures.Fixture):

    def __init__(self, db_api, db_migrate, sql_connection,
                 sqlite_db, sqlite_clean_db):
        self.sql_connection = sql_connection
        self.sqlite_db = sqlite_db
        self.sqlite_clean_db = sqlite_clean_db

        # Suppress logging for test runs
        migrate_logger = logging.getLogger('migrate')
        migrate_logger.setLevel(logging.WARNING)

        self.engine = db_api.get_engine()
        self.engine.dispose()
        conn = self.engine.connect()
        db_migrate.db_sync()
        if sql_connection == "sqlite://":
            conn = self.engine.connect()
            self._DB = "".join(line for line in conn.connection.iterdump())
            self.engine.dispose()
        else:
            cleandb = os.path.join(CONF.state_path, sqlite_clean_db)
            testdb = os.path.join(CONF.state_path, sqlite_db)
            shutil.copyfile(testdb, cleandb)

    def setUp(self):
        super(Database, self).setUp()

        if self.sql_connection == "sqlite://":
            conn = self.engine.connect()
            conn.connection.executescript(self._DB)
            self.addCleanup(self.engine.dispose)
        else:
            shutil.copyfile(
                os.path.join(CONF.state_path, self.sqlite_clean_db),
                os.path.join(CONF.state_path, self.sqlite_db))


class TestCase(base.BaseTestCase):

    """Test case base class for all unit tests."""

    def setUp(self):
        """Run before each test method to initialize test environment."""
        super(TestCase, self).setUp()

        conf_fixture.set_defaults(CONF)
        CONF([], default_config_files=[])

        CONF.set_default('connection', 'sqlite://', 'database')
        CONF.set_default('sqlite_synchronous', False, 'database')

        global _DB_CACHE
        if not _DB_CACHE:
            _DB_CACHE = Database(sqla_api, migration,
                                 sql_connection=CONF.database.connection,
                                 sqlite_db=CONF.database.sqlite_db,
                                 sqlite_clean_db=CONF.sqlite_clean_db)
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
