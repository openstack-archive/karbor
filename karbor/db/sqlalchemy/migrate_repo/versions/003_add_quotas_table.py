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

from sqlalchemy import Boolean, Column, DateTime, Integer
from sqlalchemy import MetaData, String, Table, ForeignKey


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    quotas = Table(
        'quotas', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', Integer, primary_key=True),
        Column('project_id', String(length=255), nullable=False),
        Column('resource', String(length=255), nullable=False),
        Column('hard_limit', Integer),
        mysql_engine='InnoDB'
    )

    quotas.create()

    quota_classes = Table(
        'quota_classes', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', Integer, primary_key=True),
        Column('class_name', String(length=255), nullable=False),
        Column('resource', String(length=255), nullable=False),
        Column('hard_limit', Integer),
        mysql_engine='InnoDB'
    )
    quota_classes.create()

    quota_usages = Table(
        'quota_usages', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', Integer, primary_key=True),
        Column('project_id', String(length=255), nullable=False),
        Column('resource', String(length=255), nullable=False),
        Column('in_use', Integer),
        Column('reserved', Integer),
        Column('until_refresh', Integer, nullable=True),
        mysql_engine='InnoDB'
    )

    quota_usages.create()

    reservations = Table(
        'reservations', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Boolean),
        Column('id', Integer, primary_key=True),
        Column('uuid', String(length=36), nullable=False),
        Column('usage_id', Integer, ForeignKey('quota_usages.id'),
               nullable=False),
        Column('project_id', String(length=255), index=True),
        Column('resource', String(length=255)),
        Column('delta', Integer, nullable=False),
        Column('expire', DateTime),
        mysql_engine='InnoDB'
    )

    reservations.create()
