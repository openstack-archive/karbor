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
SQLAlchemy models for smaug data.
"""

from oslo_config import cfg
from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
from sqlalchemy import Column, Integer, String, Text, schema
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import DateTime, Boolean, Index, ForeignKey

CONF = cfg.CONF
BASE = declarative_base()


class SmaugBase(models.TimestampMixin,
                models.ModelBase):
    """Base class for Smaug Models."""

    __table_args__ = {'mysql_engine': 'InnoDB'}

    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    metadata = None

    def delete(self, session):
        """Delete this object."""
        self.deleted = True
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)


class Service(BASE, SmaugBase):
    """Represents a running service on a host."""

    __tablename__ = 'services'
    id = Column(Integer, primary_key=True)
    host = Column(String(255))  # , ForeignKey('hosts.id'))
    binary = Column(String(255))
    topic = Column(String(255))
    report_count = Column(Integer, nullable=False, default=0)
    disabled = Column(Boolean, default=False)
    disabled_reason = Column(String(255))
    # adding column modified_at to contain timestamp
    # for manual enable/disable of smaug services
    # updated_at column will now contain timestamps for
    # periodic updates
    modified_at = Column(DateTime)
    rpc_current_version = Column(String(36))
    rpc_available_version = Column(String(36))


class ScheduledOperationState(BASE, SmaugBase):
    """Represents a scheduled operation state."""

    __tablename__ = 'scheduled_operation_states'
    __table_args__ = (
        Index('operation_id_idx', 'operation_id', unique=True),
        schema.UniqueConstraint('operation_id', name='uniq_operation_id'),
    )

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    # TODO(chenzeng):add foreign key after scheduled_operations is defined.
    # operation_id = Column(String(36),
    #                       ForeignKey('scheduled_operations.id',
    #                                  ondelete='CASCADE'),
    #                       nullable=False)
    operation_id = Column(String(36), nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    state = Column(String(32), nullable=False)


class ScheduledOperationLog(BASE, SmaugBase):
    """Represents a scheduled operation log."""

    __tablename__ = 'scheduled_operation_logs'
    __table_args__ = (
        Index('operation_id_idx', 'operation_id'),
    )

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    # TODO(chenzeng):add foreign key after scheduled_operations is defined.
    # operation_id = Column(String(36),
    #                       ForeignKey('scheduled_operations.id',
    #                                  ondelete='CASCADE'),
    #                       nullable=False)
    operation_id = Column(String(36), nullable=False)
    expect_start_time = Column(DateTime)
    triggered_time = Column(DateTime)
    actual_start_time = Column(DateTime)
    end_time = Column(DateTime)
    state = Column(String(32), nullable=False)
    extend_info = Column(Text)


def register_models():
    """Register Models and create metadata.

    Called from smaug.db.sqlalchemy.__init__ as part of loading the driver,
    it will never need to be called explicitly elsewhere unless the
    connection is lost and needs to be reestablished.
    """
    from sqlalchemy import create_engine
    models = (Service,)
    engine = create_engine(CONF.database.connection, echo=False)
    for model in models:
        model.metadata.create_all(engine)
