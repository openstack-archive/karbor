#   Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import MetaData, String, Table, Text


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    # New table
    verifications = Table(
        'verifications', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', String(36), primary_key=True, nullable=False),
        Column('project_id', String(length=255), nullable=False),
        Column('provider_id', String(length=36), nullable=False),
        Column('checkpoint_id', String(length=36), nullable=False),
        Column('status', String(length=64)),
        Column('parameters', Text),
        Column('resources_status', Text),
        Column('resources_reason', Text),
        mysql_engine='InnoDB'
    )

    verifications.create()
