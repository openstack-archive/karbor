=======================
Using the Karbor Client
=======================

Environment Variables
---------------------

To use cinder or karbor client, we should provide Keystone authentication
variables.

.. code-block:: console

    export OS_USERNAME=admin
    export OS_PASSWORD=123456
    export OS_TENANT_NAME=admin
    export OS_AUTH_URL=http://10.229.47.230/identity/

Provider
--------

List the provider

.. code-block:: console

    karbor provider-list
    +--------------------------------------+-------------------+-------------------------------------------------------------------------------------+
    | Id                                   | Name              | Description                                                                         |
    +--------------------------------------+-------------------+-------------------------------------------------------------------------------------+
    | b766f37c-d011-4026-8228-28730d734a3f | No-Op Provider    | This provider does nothing for each protect and restore operation. Used for testing |
    | cf56bd3e-97a7-4078-b6d5-f36246333fd9 | OS Infra Provider | This provider uses OpenStack's own services (swift, cinder) as storage              |
    | e4008868-be97-492c-be41-44e50ef2e16f | EISOO Provider    | This provider provides data protection for applications with EISOO AnyBackup        |
    +--------------------------------------+-------------------+-------------------------------------------------------------------------------------+

Show the provider information

.. code-block:: console

    karbor provider-show cf56bd3e-97a7-4078-b6d5-f36246333fd9
    +----------------------+---------------------------------------------------------------------------------------------+
    | Property             | Value                                                                                       |
    +----------------------+---------------------------------------------------------------------------------------------+
    | description          | This provider uses OpenStack's own services (swift, cinder) as storage                      |
    | extended_info_schema | {                                                                                           |
    |                      |   "options_schema": {                                                                       |
    |                      |     "OS::Cinder::Volume": {                                                                 |
    |                      |       "properties": {                                                                       |
    |                      |         "backup_mode": {                                                                    |
    |                      |           "default": "auto",                                                                |
    |                      |           "description": "The backup mode.",                                                |
    |                      |           "enum": [                                                                         |
    |                      |             "full",                                                                         |
    |                      |             "incremental",                                                                  |
    |                      |             "auto"                                                                          |
    |                      |           ],                                                                                |
    |                      |           "title": "Backup Mode",                                                           |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "backup_name": {                                                                    |
    |                      |           "description": "The name of the backup.",                                         |
    |                      |           "title": "Backup Name",                                                           |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "container": {                                                                      |
    |                      |           "description": "The container which been chosen.",                                |
    |                      |           "title": "Container",                                                             |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "description": {                                                                    |
    |                      |           "description": "The description of the volume.",                                  |
    |                      |           "title": "Description",                                                           |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "force": {                                                                          |
    |                      |           "default": false,                                                                 |
    |                      |           "description": "Whether to backup, even if the volumeis attached",                |
    |                      |           "title": "Force",                                                                 |
    |                      |           "type": "boolean"                                                                 |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [                                                                         |
    |                      |         "backup_name",                                                                      |
    |                      |         "backup_mode",                                                                      |
    |                      |         "container",                                                                        |
    |                      |         "force"                                                                             |
    |                      |       ],                                                                                    |
    |                      |       "title": "Cinder Protection Options",                                                 |
    |                      |       "type": "object"                                                                      |
    |                      |     },                                                                                      |
    |                      |     "OS::Glance::Image": {                                                                  |
    |                      |       "properties": {                                                                       |
    |                      |         "backup_name": {                                                                    |
    |                      |           "default": null,                                                                  |
    |                      |           "description": "The name of the backup.",                                         |
    |                      |           "title": "Backup Name",                                                           |
    |                      |           "type": "string"                                                                  |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [],                                                                       |
    |                      |       "title": "Image Protection Options",                                                  |
    |                      |       "type": "object"                                                                      |
    |                      |     },                                                                                      |
    |                      |     "OS::Nova::Server": {                                                                   |
    |                      |       "properties": {},                                                                     |
    |                      |       "required": [],                                                                       |
    |                      |       "title": "Server Protection Options",                                                 |
    |                      |       "type": "object"                                                                      |
    |                      |     }                                                                                       |
    |                      |   },                                                                                        |
    |                      |   "restore_schema": {                                                                       |
    |                      |     "OS::Cinder::Volume": {                                                                 |
    |                      |       "properties": {                                                                       |
    |                      |         "restore_description": {                                                            |
    |                      |           "default": null,                                                                  |
    |                      |           "description": "The description of the restored volume.",                         |
    |                      |           "title": "Restore Description",                                                   |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "restore_name": {                                                                   |
    |                      |           "default": null,                                                                  |
    |                      |           "description": "The name of the restored volume.",                                |
    |                      |           "title": "Restore Name",                                                          |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "volume_id": {                                                                      |
    |                      |           "description": "The target volume ID to restore to.",                             |
    |                      |           "title": "Volume ID",                                                             |
    |                      |           "type": "string"                                                                  |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "title": "Cinder Protection Restore",                                                 |
    |                      |       "type": "object"                                                                      |
    |                      |     },                                                                                      |
    |                      |     "OS::Glance::Image": {                                                                  |
    |                      |       "properties": {                                                                       |
    |                      |         "restore_name": {                                                                   |
    |                      |           "description": "The name of the restore image",                                   |
    |                      |           "title": "Restore Image Name",                                                    |
    |                      |           "type": "string"                                                                  |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [                                                                         |
    |                      |         "backup_name"                                                                       |
    |                      |       ],                                                                                    |
    |                      |       "title": "Image Protection Restore",                                                  |
    |                      |       "type": "object"                                                                      |
    |                      |     },                                                                                      |
    |                      |     "OS::Nova::Server": {                                                                   |
    |                      |       "properties": {                                                                       |
    |                      |         "restore_name": {                                                                   |
    |                      |           "description": "The name of the restore server",                                  |
    |                      |           "title": "Restore Server Name",                                                   |
    |                      |           "type": "string"                                                                  |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [                                                                         |
    |                      |         "restore_name"                                                                      |
    |                      |       ],                                                                                    |
    |                      |       "title": "Server Protection Restore",                                                 |
    |                      |       "type": "object"                                                                      |
    |                      |     }                                                                                       |
    |                      |   },                                                                                        |
    |                      |   "saved_info_schema": {                                                                    |
    |                      |     "OS::Cinder::Volume": {                                                                 |
    |                      |       "properties": {                                                                       |
    |                      |         "fail_reason": {                                                                    |
    |                      |           "description": "The reason for the failure status of the backup.",                |
    |                      |           "title": "Fail Reason",                                                           |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "is_incremental": {                                                                 |
    |                      |           "description": "The type of the backup, True is incremental and False is full.",  |
    |                      |           "title": "Is Incremental",                                                        |
    |                      |           "type": "boolean"                                                                 |
    |                      |         },                                                                                  |
    |                      |         "name": {                                                                           |
    |                      |           "description": "The name for this backup.",                                       |
    |                      |           "title": "Name",                                                                  |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "progress": {                                                                       |
    |                      |           "constraint": {                                                                   |
    |                      |             "max": 1,                                                                       |
    |                      |             "min": 0                                                                        |
    |                      |           },                                                                                |
    |                      |           "description": "The current operation progress for this backup.",                 |
    |                      |           "title": "Progress",                                                              |
    |                      |           "type": "number"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "size": {                                                                           |
    |                      |           "description": "The size of the backup, in GB.",                                  |
    |                      |           "title": "Size",                                                                  |
    |                      |           "type": "integer"                                                                 |
    |                      |         },                                                                                  |
    |                      |         "status": {                                                                         |
    |                      |           "description": "The backup status, such as available.",                           |
    |                      |           "enum": [                                                                         |
    |                      |             "creating",                                                                     |
    |                      |             "available",                                                                    |
    |                      |             "deleting",                                                                     |
    |                      |             "error",                                                                        |
    |                      |             "restoring",                                                                    |
    |                      |             "error_restoring"                                                               |
    |                      |           ],                                                                                |
    |                      |           "title": "Status",                                                                |
    |                      |           "type": "string"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "volume_id": {                                                                      |
    |                      |           "description": "The ID of the volume from which the backup was created.",         |
    |                      |           "title": "Volume ID",                                                             |
    |                      |           "type": "string"                                                                  |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [                                                                         |
    |                      |         "name",                                                                             |
    |                      |         "status",                                                                           |
    |                      |         "progress",                                                                         |
    |                      |         "fail_reason",                                                                      |
    |                      |         "size",                                                                             |
    |                      |         "volume_id"                                                                         |
    |                      |       ],                                                                                    |
    |                      |       "title": "Cinder Protection Saved Info",                                              |
    |                      |       "type": "object"                                                                      |
    |                      |     },                                                                                      |
    |                      |     "OS::Glance::Image": {                                                                  |
    |                      |       "properties": {                                                                       |
    |                      |         "image_metadata": {                                                                 |
    |                      |           "description": "To save disk_format and container_format",                        |
    |                      |           "title": "Image Metadata",                                                        |
    |                      |           "type": "image"                                                                   |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [                                                                         |
    |                      |         "image_metadata"                                                                    |
    |                      |       ],                                                                                    |
    |                      |       "title": "Image Protection Saved Info",                                               |
    |                      |       "type": "object"                                                                      |
    |                      |     },                                                                                      |
    |                      |     "OS::Nova::Server": {                                                                   |
    |                      |       "properties": {                                                                       |
    |                      |         "attach_metadata": {                                                                |
    |                      |           "description": "The devices of attached volumes",                                 |
    |                      |           "title": "Attached Volume Metadata",                                              |
    |                      |           "type": "object"                                                                  |
    |                      |         },                                                                                  |
    |                      |         "snapshot_metadata": {                                                              |
    |                      |           "description": "The metadata of snapshot",                                        |
    |                      |           "title": "Snapshot Metadata",                                                     |
    |                      |           "type": "object"                                                                  |
    |                      |         }                                                                                   |
    |                      |       },                                                                                    |
    |                      |       "required": [                                                                         |
    |                      |         "attached_metadata",                                                                |
    |                      |         "snapshot_metadata"                                                                 |
    |                      |       ],                                                                                    |
    |                      |       "title": "Server Protection Saved Info",                                              |
    |                      |       "type": "object"                                                                      |
    |                      |     }                                                                                       |
    |                      |   }                                                                                         |
    |                      | }                                                                                           |
    | id                   | cf56bd3e-97a7-4078-b6d5-f36246333fd9                                                        |
    | name                 | OS Infra Provider                                                                           |
    +----------------------+---------------------------------------------------------------------------------------------+

Protectables
------------

Use cinder client to create volumes

.. code-block:: console

    cinder create 1 --name volume1
    cinder create 1 --name volume2
    cinder list
    +--------------------------------------+-----------+---------+------+-------------+----------+-------------+
    | ID                                   | Status    | Name    | Size | Volume Type | Bootable | Attached to |
    +--------------------------------------+-----------+---------+------+-------------+----------+-------------+
    | 12e2abc6-f20b-430d-9b36-1a6befd23b6c | available | volume2 | 1    | lvmdriver-1 | false    |             |
    | 700495ee-38e6-41a0-963f-f3f9a24c0f75 | available | volume1 | 1    | lvmdriver-1 | false    |             |
    +--------------------------------------+-----------+---------+------+-------------+----------+-------------+

List the protectable resources

.. code-block:: console

    karbor protectable-list
    +-----------------------+
    | Protectable type      |
    +-----------------------+
    | OS::Cinder::Volume    |
    | OS::Glance::Image     |
    | OS::Keystone::Project |
    | OS::Nova::Server      |
    +-----------------------+
    karbor protectable-show OS::Nova::Server
    +-----------------+-----------------------------------------------+
    | Property        | Value                                         |
    +-----------------+-----------------------------------------------+
    | dependent_types | [u'OS::Cinder::Volume', u'OS::Glance::Image'] |
    | name            | OS::Nova::Server                              |
    +-----------------+-----------------------------------------------+
    karbor protectable-list-instances OS::Cinder::Volume
    +--------------------------------------+--------------------+---------------------+
    | Id                                   | Type               | Dependent resources |
    +--------------------------------------+--------------------+---------------------+
    | 12e2abc6-f20b-430d-9b36-1a6befd23b6c | OS::Cinder::Volume | []                  |
    | 700495ee-38e6-41a0-963f-f3f9a24c0f75 | OS::Cinder::Volume | []                  |
    +--------------------------------------+--------------------+---------------------+
    karbor protectable-show-instance OS::Cinder::Volume 12e2abc6-f20b-430d-9b36-1a6befd23b6c
    +---------------------+--------------------------------------+
    | Property            | Value                                |
    +---------------------+--------------------------------------+
    | dependent_resources | []                                   |
    | id                  | 12e2abc6-f20b-430d-9b36-1a6befd23b6c |
    | name                | volume2                              |
    | type                | OS::Cinder::Volume                   |
    +---------------------+--------------------------------------+

Plans
-----
Create a protection plan with a provider and resources

.. code-block:: console

    karbor plan-create 'OS volumes protection plan.' 'cf56bd3e-97a7-4078-b6d5-f36246333fd9' '12e2abc6-f20b-430d-9b36-1a6befd23b6c'='OS::Cinder::Volume'='volume2','700495ee-38e6-41a0-963f-f3f9a24c0f75'='OS::Cinder::Volume'='volume1'
    +-------------+----------------------------------------------------+
    | Property    | Value                                              |
    +-------------+----------------------------------------------------+
    | description | None                                               |
    | id          | ef8b83f3-d0c4-48ec-8949-5c72bbf14103               |
    | name        | OS volumes protection plan.                        |
    | parameters  | {}                                                 |
    | provider_id | cf56bd3e-97a7-4078-b6d5-f36246333fd9               |
    | resources   | [                                                  |
    |             |   {                                                |
    |             |     "id": "12e2abc6-f20b-430d-9b36-1a6befd23b6c",  |
    |             |     "name": "volume2",                             |
    |             |     "type": "OS::Cinder::Volume"                   |
    |             |   },                                               |
    |             |   {                                                |
    |             |     "id": "700495ee-38e6-41a0-963f-f3f9a24c0f75",  |
    |             |     "name": "volume1",                             |
    |             |     "type": "OS::Cinder::Volume"                   |
    |             |   }                                                |
    |             | ]                                                  |
    | status      | suspended                                          |
    +-------------+----------------------------------------------------+

Checkpoints
-----------
Execute a protect operation manually with a plan

.. code-block:: console

    karbor checkpoint-create cf56bd3e-97a7-4078-b6d5-f36246333fd9 ef8b83f3-d0c4-48ec-8949-5c72bbf14103
    +-----------------+------------------------------------------------------+
    | Property        | Value                                                |
    +-----------------+------------------------------------------------------+
    | created_at      | None                                                 |
    | extra_info      | {"created_by": "manual"}                             |
    | id              | 80f6154f-cc43-441f-8841-35ae23e17f4f                 |
    | project_id      | 31478a6f980d4e73a3bdac3ad04a3605                     |
    | protection_plan | {                                                    |
    |                 |   "id": "ef8b83f3-d0c4-48ec-8949-5c72bbf14103",      |
    |                 |   "name": "OS volumes protection plan.",             |
    |                 |   "resources": [                                     |
    |                 |     {                                                |
    |                 |       "id": "12e2abc6-f20b-430d-9b36-1a6befd23b6c",  |
    |                 |       "name": "volume2",                             |
    |                 |       "type": "OS::Cinder::Volume"                   |
    |                 |     },                                               |
    |                 |     {                                                |
    |                 |       "id": "700495ee-38e6-41a0-963f-f3f9a24c0f75",  |
    |                 |       "name": "volume1",                             |
    |                 |       "type": "OS::Cinder::Volume"                   |
    |                 |     }                                                |
    |                 |   ]                                                  |
    |                 | }                                                    |
    | resource_graph  | None                                                 |
    | status          | protecting                                           |
    +-----------------+------------------------------------------------------+
    # check the protect result
    cinder backup-list
    +--------------------------------------+--------------------------------------+-----------+------+------+--------------+---------------+
    | ID                                   | Volume ID                            | Status    | Name | Size | Object Count | Container     |
    +--------------------------------------+--------------------------------------+-----------+------+------+--------------+---------------+
    | becf53cd-12f8-424d-9b08-54fbffe9495a | 700495ee-38e6-41a0-963f-f3f9a24c0f75 | available | -    | 1    | 22           | volumebackups |
    | c35317f4-df2a-4c7d-9f36-6495c563a5bf | 12e2abc6-f20b-430d-9b36-1a6befd23b6c | available | -    | 1    | 22           | volumebackups |
    +--------------------------------------+--------------------------------------+-----------+------+------+--------------+---------------+
    karbor checkpoint-show cf56bd3e-97a7-4078-b6d5-f36246333fd9 80f6154f-cc43-441f-8841-35ae23e17f4f
    +-----------------+-----------------------------------------------------------+
    | Property        | Value                                                     |
    +-----------------+-----------------------------------------------------------+
    | created_at      | 2017-02-13                                                |
    | extra_info      | {"created_by": "manual"}                                  |
    | id              | 80f6154f-cc43-441f-8841-35ae23e17f4f                      |
    | project_id      | 31478a6f980d4e73a3bdac3ad04a3605                          |
    | protection_plan | {                                                         |
    |                 |   "id": "ef8b83f3-d0c4-48ec-8949-5c72bbf14103",           |
    |                 |   "name": "OS volumes protection plan.",                  |
    |                 |   "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",  |
    |                 |   "resources": [                                          |
    |                 |     {                                                     |
    |                 |       "id": "12e2abc6-f20b-430d-9b36-1a6befd23b6c",       |
    |                 |       "name": "volume2",                                  |
    |                 |       "type": "OS::Cinder::Volume"                        |
    |                 |     },                                                    |
    |                 |     {                                                     |
    |                 |       "id": "700495ee-38e6-41a0-963f-f3f9a24c0f75",       |
    |                 |       "name": "volume1",                                  |
    |                 |       "type": "OS::Cinder::Volume"                        |
    |                 |     }                                                     |
    |                 |   ]                                                       |
    |                 | }                                                         |
    | resource_graph  | [                                                         |
    |                 |   {                                                       |
    |                 |     "0x0": [                                              |
    |                 |       "OS::Cinder::Volume",                               |
    |                 |       "700495ee-38e6-41a0-963f-f3f9a24c0f75",             |
    |                 |       "volume1"                                           |
    |                 |     ],                                                    |
    |                 |     "0x1": [                                              |
    |                 |       "OS::Cinder::Volume",                               |
    |                 |       "12e2abc6-f20b-430d-9b36-1a6befd23b6c",             |
    |                 |       "volume2"                                           |
    |                 |     ]                                                     |
    |                 |   },                                                      |
    |                 |   []                                                      |
    |                 | ]                                                         |
    | status          | available                                                 |
    +-----------------+-----------------------------------------------------------+

Restores
--------

Execute a restore operation manually with a checkpoint id

.. code-block:: console

    karbor restore-create cf56bd3e-97a7-4078-b6d5-f36246333fd9 80f6154f-cc43-441f-8841-35ae23e17f4f
    +------------------+--------------------------------------+
    | Property         | Value                                |
    +------------------+--------------------------------------+
    | checkpoint_id    | 80f6154f-cc43-441f-8841-35ae23e17f4f |
    | id               | f30cb640-594a-487b-9569-c26fd5861c95 |
    | parameters       | {}                                   |
    | project_id       | 31478a6f980d4e73a3bdac3ad04a3605     |
    | provider_id      | cf56bd3e-97a7-4078-b6d5-f36246333fd9 |
    | resources_reason | {}                                   |
    | resources_status | {}                                   |
    | restore_target   | None                                 |
    | status           | in_progress                          |
    +------------------+--------------------------------------+
    karbor restore-show f30cb640-594a-487b-9569-c26fd5861c95
    +------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
    | Property         | Value                                                                                                                                                |
    +------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
    | checkpoint_id    | 80f6154f-cc43-441f-8841-35ae23e17f4f                                                                                                                 |
    | id               | f30cb640-594a-487b-9569-c26fd5861c95                                                                                                                 |
    | parameters       | {}                                                                                                                                                   |
    | project_id       | 31478a6f980d4e73a3bdac3ad04a3605                                                                                                                     |
    | provider_id      | cf56bd3e-97a7-4078-b6d5-f36246333fd9                                                                                                                 |
    | resources_reason | {}                                                                                                                                                   |
    | resources_status | {u'OS::Cinder::Volume#2b6e0055-bec0-41f5-85fa-a830a3684fd9': u'available', u'OS::Cinder::Volume#6c77fd44-c76b-400e-8aa4-97bce241b690': u'available'} |
    | restore_target   | None                                                                                                                                                 |
    | status           | success                                                                                                                                              |
    +------------------+------------------------------------------------------------------------------------------------------------------------------------------------------+
    cinder list
    +--------------------------------------+-----------+---------------------------------------------------------------------------+------+-------------+----------+-------------+
    | ID                                   | Status    | Name                                                                      | Size | Volume Type | Bootable | Attached to |
    +--------------------------------------+-----------+---------------------------------------------------------------------------+------+-------------+----------+-------------+
    | 12e2abc6-f20b-430d-9b36-1a6befd23b6c | available | volume2                                                                   | 1    | lvmdriver-1 | false    |             |
    | 2b6e0055-bec0-41f5-85fa-a830a3684fd9 | available | 80f6154f-cc43-441f-8841-35ae23e17f4f@12e2abc6-f20b-430d-9b36-1a6befd23b6c | 1    | lvmdriver-1 | false    |             |
    | 6c77fd44-c76b-400e-8aa4-97bce241b690 | available | 80f6154f-cc43-441f-8841-35ae23e17f4f@700495ee-38e6-41a0-963f-f3f9a24c0f75 | 1    | lvmdriver-1 | false    |             |
    | 700495ee-38e6-41a0-963f-f3f9a24c0f75 | available | volume1                                                                   | 1    | lvmdriver-1 | false    |             |
    +--------------------------------------+-----------+---------------------------------------------------------------------------+------+-------------+----------+-------------+

Checkpoint Delete
-----------------

Execute a delete operation manually with a checkpoint id

.. code-block:: console

    cinder backup-list
    +--------------------------------------+--------------------------------------+-----------+------+------+--------------+---------------+
    | ID                                   | Volume ID                            | Status    | Name | Size | Object Count | Container     |
    +--------------------------------------+--------------------------------------+-----------+------+------+--------------+---------------+
    | becf53cd-12f8-424d-9b08-54fbffe9495a | 700495ee-38e6-41a0-963f-f3f9a24c0f75 | available | -    | 1    | 22           | volumebackups |
    | c35317f4-df2a-4c7d-9f36-6495c563a5bf | 12e2abc6-f20b-430d-9b36-1a6befd23b6c | available | -    | 1    | 22           | volumebackups |
    +--------------------------------------+--------------------------------------+-----------+------+------+--------------+---------------+

    karbor checkpoint-delete cf56bd3e-97a7-4078-b6d5-f36246333fd9 80f6154f-cc43-441f-8841-35ae23e17f4f

    cinder backup-list
    +----+-----------+--------+------+------+--------------+-----------+
    | ID | Volume ID | Status | Name | Size | Object Count | Container |
    +----+-----------+--------+------+------+--------------+-----------+
    +----+-----------+--------+------+------+--------------+-----------+

Checkpoint Reset State
----------------------

Execute a reset state operation manually with a checkpoint id

.. code-block:: console

    karbor checkpoint-reset-state cf56bd3e-97a7-4078-b6d5-f36246333fd9 80f6154f-cc43-441f-8841-35ae23e17f4f --available

    # check the checkpoint status
    karbor checkpoint-show cf56bd3e-97a7-4078-b6d5-f36246333fd9 80f6154f-cc43-441f-8841-35ae23e17f4f
    +-----------------+-----------------------------------------------------------+
    | Property        | Value                                                     |
    +-----------------+-----------------------------------------------------------+
    | created_at      | 2017-02-13                                                |
    | extra_info      | {"created_by": "manual"}                                  |
    | id              | 80f6154f-cc43-441f-8841-35ae23e17f4f                      |
    | project_id      | 31478a6f980d4e73a3bdac3ad04a3605                          |
    | protection_plan | {                                                         |
    |                 |   "id": "ef8b83f3-d0c4-48ec-8949-5c72bbf14103",           |
    |                 |   "name": "OS volumes protection plan.",                  |
    |                 |   "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",  |
    |                 |   "resources": [                                          |
    |                 |     {                                                     |
    |                 |       "id": "12e2abc6-f20b-430d-9b36-1a6befd23b6c",       |
    |                 |       "name": "volume2",                                  |
    |                 |       "type": "OS::Cinder::Volume"                        |
    |                 |     },                                                    |
    |                 |     {                                                     |
    |                 |       "id": "700495ee-38e6-41a0-963f-f3f9a24c0f75",       |
    |                 |       "name": "volume1",                                  |
    |                 |       "type": "OS::Cinder::Volume"                        |
    |                 |     }                                                     |
    |                 |   ]                                                       |
    |                 | }                                                         |
    | resource_graph  | [                                                         |
    |                 |   {                                                       |
    |                 |     "0x0": [                                              |
    |                 |       "OS::Cinder::Volume",                               |
    |                 |       "700495ee-38e6-41a0-963f-f3f9a24c0f75",             |
    |                 |       "volume1"                                           |
    |                 |     ],                                                    |
    |                 |     "0x1": [                                              |
    |                 |       "OS::Cinder::Volume",                               |
    |                 |       "12e2abc6-f20b-430d-9b36-1a6befd23b6c",             |
    |                 |       "volume2"                                           |
    |                 |     ]                                                     |
    |                 |   },                                                      |
    |                 |   []                                                      |
    |                 | ]                                                         |
    | status          | available                                                 |
    +-----------------+-----------------------------------------------------------+

Scheduled Opeartions
--------------------

Execute a protect operation automatically with a scheduler

.. code-block:: console

    karbor trigger-create 'My Trigger' 'time' "pattern"="BEGIN:VEVENT\nRRULE:FREQ=MINUTELY;INTERVAL=5;\nEND:VEVENT","format"="calendar"
    +------------+------------------------------------------------------------------------------+
    | Property   | Value                                                                        |
    +------------+------------------------------------------------------------------------------+
    | id         | b065836f-6485-429d-b12c-e04395c5f58e                                         |
    | name       | My Trigger                                                                   |
    | properties | {                                                                            |
    |            |   "format": "calendar",                                                      |
    |            |   "pattern": "BEGIN:VEVENT\\nRRULE:FREQ=MINUTELY;INTERVAL=5;\\nEND:VEVENT",  |
    |            |   "start_time": "2017-03-02 22:56:42"                                        |
    |            | }                                                                            |
    | type       | time                                                                         |
    +------------+------------------------------------------------------------------------------+
    karbor scheduledoperation-create 'Protect with My Trigger' protect b065836f-6485-429d-b12c-e04395c5f58e "plan_id"="ca572b42-6d35-4d81-bb4e-c9b100a3387a","provider_id"="cf56bd3e-97a7-4078-b6d5-f36246333fd9"
    +----------------------+---------------------------------------------------------+
    | Property             | Value                                                   |
    +----------------------+---------------------------------------------------------+
    | description          | None                                                    |
    | enabled              | True                                                    |
    | id                   | 2ebcf7cc-d8fe-4a70-af71-8a13f20556fb                    |
    | name                 | PMT                                                     |
    | operation_definition | {                                                       |
    |                      |   "plan_id": "ca572b42-6d35-4d81-bb4e-c9b100a3387a",    |
    |                      |   "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9" |
    |                      | }                                                       |
    | operation_type       | protect                                                 |
    | trigger_id           | b065836f-6485-429d-b12c-e04395c5f58e                    |
    +----------------------+---------------------------------------------------------+
    karbor checkpoint-list cf56bd3e-97a7-4078-b6d5-f36246333fd9
    +--------------------------------------+----------------------------------+-----------+-----------------------------------------------------------+------------+
    | Id                                   | Project id                       | Status    | Protection plan                                           | Created at |
    +--------------------------------------+----------------------------------+-----------+-----------------------------------------------------------+------------+
    | 92e74f0c-8519-4928-9bd5-0039e0fe92b0 | 9632a0c585c94d708c57a83190913c76 | available | {                                                         | 2017-03-03 |
    |                                      |                                  |           |   "id": "ca572b42-6d35-4d81-bb4e-c9b100a3387a",           |            |
    |                                      |                                  |           |   "name": "Plan1",                                        |            |
    |                                      |                                  |           |   "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",  |            |
    |                                      |                                  |           |   "resources": [                                          |            |
    |                                      |                                  |           |     {                                                     |            |
    |                                      |                                  |           |       "id": "d72e83c2-4083-4cc7-9283-4578332732ab",       |            |
    |                                      |                                  |           |       "name": "Volume1",                                  |            |
    |                                      |                                  |           |       "type": "OS::Cinder::Volume"                        |            |
    |                                      |                                  |           |     }                                                     |            |
    |                                      |                                  |           |   ]                                                       |            |
    |                                      |                                  |           | }                                                         |            |
    +--------------------------------------+----------------------------------+-----------+-----------------------------------------------------------+------------+
