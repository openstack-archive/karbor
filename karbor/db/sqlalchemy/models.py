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
SQLAlchemy models for karbor data.
"""

from oslo_config import cfg
from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import DateTime, Boolean, ForeignKey
from sqlalchemy import orm

CONF = cfg.CONF
BASE = declarative_base()


class KarborBase(models.TimestampMixin,
                 models.ModelBase):
    """Base class for karbor Models."""

    __table_args__ = {'mysql_engine': 'InnoDB'}

    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    metadata = None

    def delete(self, session):
        """Delete this object."""
        self.deleted = True
        self.deleted_at = timeutils.utcnow()
        self.save(session=session)


class Service(BASE, KarborBase):
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
    # for manual enable/disable of karbor services
    # updated_at column will now contain timestamps for
    # periodic updates
    modified_at = Column(DateTime)
    rpc_current_version = Column(String(36))
    rpc_available_version = Column(String(36))


class Trigger(BASE, KarborBase):
    """Represents a trigger."""

    __tablename__ = 'triggers'

    id = Column(String(36), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    project_id = Column(String(255), nullable=False)
    type = Column(String(64), nullable=False)
    properties = Column(Text, nullable=False)


class ScheduledOperation(BASE, KarborBase):
    """Represents a scheduled operation."""

    __tablename__ = 'scheduled_operations'

    id = Column(String(36), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(255))
    operation_type = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)
    project_id = Column(String(255), nullable=False)
    trigger_id = Column(String(36), ForeignKey('triggers.id'),
                        index=True, nullable=False)
    operation_definition = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)

    trigger = orm.relationship(
        Trigger,
        foreign_keys=trigger_id,
        primaryjoin='and_('
                    'ScheduledOperation.trigger_id == Trigger.id,'
                    'ScheduledOperation.deleted == 0,'
                    'Trigger.deleted == 0)')


class ScheduledOperationState(BASE, KarborBase):
    """Represents a scheduled operation state."""

    __tablename__ = 'scheduled_operation_states'

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    operation_id = Column(String(36),
                          ForeignKey('scheduled_operations.id',
                                     ondelete='CASCADE'),
                          index=True, unique=True,
                          nullable=False)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    trust_id = Column(String(64), nullable=False)
    state = Column(String(32), nullable=False)
    end_time_for_run = Column(DateTime)

    operation = orm.relationship(
        ScheduledOperation,
        foreign_keys=operation_id,
        primaryjoin='and_('
                    'ScheduledOperationState.operation_id == '
                    'ScheduledOperation.id,'
                    'ScheduledOperationState.deleted == 0,'
                    'ScheduledOperation.deleted == 0)')


class ScheduledOperationLog(BASE, KarborBase):
    """Represents a scheduled operation log."""

    __tablename__ = 'scheduled_operation_logs'

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    operation_id = Column(String(36),
                          ForeignKey('scheduled_operations.id',
                                     ondelete='CASCADE'),
                          index=True, nullable=False)
    expect_start_time = Column(DateTime)
    triggered_time = Column(DateTime)
    actual_start_time = Column(DateTime)
    end_time = Column(DateTime)
    state = Column(String(32), nullable=False)
    extend_info = Column(Text)


class Plan(BASE, KarborBase):
    """Represents a Plan."""

    __tablename__ = 'plans'
    id = Column(String(36), primary_key=True)
    name = Column(String(255))
    description = Column(String(255))
    provider_id = Column(String(36))
    project_id = Column(String(255))
    status = Column(String(64))
    parameters = Column(Text)


class Resource(BASE, KarborBase):
    """Represents a resource in a plan."""

    __tablename__ = 'resources'
    id = Column(Integer, primary_key=True)
    resource_id = Column(String(36))
    resource_type = Column(String(64))
    resource_name = Column(String(255))
    resource_extra_info = Column(Text)
    plan_id = Column(String(36), ForeignKey('plans.id'), nullable=False)
    plan = orm.relationship(Plan, backref="resources",
                            foreign_keys=plan_id,
                            primaryjoin='and_('
                            'Resource.plan_id == Plan.id,'
                            'Resource.deleted == False)')


class Restore(BASE, KarborBase):
    """Represents a Restore."""

    __tablename__ = 'restores'
    id = Column(String(36), primary_key=True)
    project_id = Column(String(255))
    provider_id = Column(String(36))
    checkpoint_id = Column(String(36))
    restore_target = Column(String(255))
    parameters = Column(Text)
    status = Column(String(64))
    resources_status = Column(Text)
    resources_reason = Column(Text)


class OperationLog(BASE, KarborBase):
    """Represents a operation log."""

    __tablename__ = 'operation_logs'
    id = Column(String(36), primary_key=True)
    project_id = Column(String(255))
    scheduled_operation_id = Column(String(36))
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    state = Column(String(64))
    error = Column(String(64))
    entries = Column(Text)


class CheckpointRecord(BASE, KarborBase):
    """Represents a checkpoint record."""

    __tablename__ = 'checkpoint_records'

    id = Column(String(36), primary_key=True, nullable=False)
    project_id = Column(String(36), nullable=False)
    checkpoint_id = Column(String(36), nullable=False)
    checkpoint_status = Column(String(36), nullable=False)
    provider_id = Column(String(36), nullable=False)
    plan_id = Column(String(36), nullable=False)
    operation_id = Column(String(36))
    create_by = Column(String(36))
    extend_info = Column(Text)


def register_models():
    """Register Models and create metadata.

    Called from karbor.db.sqlalchemy.__init__ as part of loading the driver,
    it will never need to be called explicitly elsewhere unless the
    connection is lost and needs to be reestablished.
    """
    from sqlalchemy import create_engine
    models = (Service,
              Plan,
              Resource,
              Trigger,
              ScheduledOperation,
              ScheduledOperationState,
              ScheduledOperationLog,
              Restore,
              CheckpointRecord)
    engine = create_engine(CONF.database.connection, echo=False)
    for model in models:
        model.metadata.create_all(engine)
