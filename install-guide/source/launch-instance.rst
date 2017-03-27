.. _launch-instance:

Launch an instance
~~~~~~~~~~~~~~~~~~

In environments that include the Data Protection service, you can create a
checkpoint and restore this checkpoint.

Create a checkpoint
-------------------

Create a checkpoint for some resource. For example, for volume:

#. Source the ``demo`` credentials to perform
   the following steps as a non-administrative project:

   .. code-block:: console

      $ . demo-openrc

#. list provider.

   .. code-block:: console

      $ karbor provider-list
      +--------------------------------------+-------------------+-------------------------------------------------------------------------------------+
      | Id                                   | Name              | Description                                                                         |
      +--------------------------------------+-------------------+-------------------------------------------------------------------------------------+
      | b766f37c-d011-4026-8228-28730d734a3f | No-Op Provider    | This provider does nothing for each protect and restore operation. Used for testing |
      | cf56bd3e-97a7-4078-b6d5-f36246333fd9 | OS Infra Provider | This provider uses OpenStack's own services (swift, cinder) as storage              |
      | e4008868-be97-492c-be41-44e50ef2e16f | EISOO Provider    | This provider provides data protection for applications with EISOO AnyBackup        |
      +--------------------------------------+-------------------+-------------------------------------------------------------------------------------+

#. list protectable.

   .. code-block:: console

      $ karbor protectable-list
      +-----------------------+
      | Protectable type      |
      +-----------------------+
      | OS::Cinder::Volume    |
      | OS::Glance::Image     |
      | OS::Keystone::Project |
      | OS::Nova::Server      |
      +-----------------------+

#. list volume resources, and get volume ID.

   .. code-block:: console

      $ openstack volume list
      +--------------------------------------+--------------+-----------+------+-------------+
      | ID                                   | Display Name | Status    | Size | Attached to |
      +--------------------------------------+--------------+-----------+------+-------------+
      | 286a43e9-3899-4983-965f-d8b1faef5e58 | Volume1      | available |    1 |             |
      +--------------------------------------+--------------+-----------+------+-------------+

#. Create a plan for this volume:

   .. code-block:: console

      $ karbor plan-create Plan1 cf56bd3e-97a7-4078-b6d5-f36246333fd9 '286a43e9-3899-4983-965f-d8b1faef5e58'='OS::Cinder::Volume'='Volume1'
      +-------------+----------------------------------------------------+
      | Property    | Value                                              |
      +-------------+----------------------------------------------------+
      | description | None                                               |
      | id          | 81ac01b7-0a69-4b0b-8ef5-bd46a900c90a               |
      | name        | Plan1                                              |
      | parameters  | {}                                                 |
      | provider_id | cf56bd3e-97a7-4078-b6d5-f36246333fd9               |
      | resources   | [                                                  |
      |             |   {                                                |
      |             |     "id": "286a43e9-3899-4983-965f-d8b1faef5e58",  |
      |             |     "name": "Volume1",                             |
      |             |     "type": "OS::Cinder::Volume"                   |
      |             |   }                                                |
      |             | ]                                                  |
      | status      | suspended                                          |
      +-------------+----------------------------------------------------+

#. Create checkpoint by plan:

   .. code-block:: console

      $ karbor checkpoint-create cf56bd3e-97a7-4078-b6d5-f36246333fd9 81ac01b7-0a69-4b0b-8ef5-bd46a900c90a
      +-----------------+------------------------------------------------------+
      | Property        | Value                                                |
      +-----------------+------------------------------------------------------+
      | created_at      | None                                                 |
      | extra_info      | None                                                 |
      | id              | c1112037-b19c-421a-83c9-dd209e785189                 |
      | project_id      | 690ccee85834425e973258252e0da888                     |
      | protection_plan | {                                                    |
      |                 |   "id": "81ac01b7-0a69-4b0b-8ef5-bd46a900c90a",      |
      |                 |   "name": "Plan1",                                   |
      |                 |   "resources": [                                     |
      |                 |     {                                                |
      |                 |       "id": "286a43e9-3899-4983-965f-d8b1faef5e58",  |
      |                 |       "name": "Volume1",                             |
      |                 |       "type": "OS::Cinder::Volume"                   |
      |                 |     }                                                |
      |                 |   ]                                                  |
      |                 | }                                                    |
      | resource_graph  | None                                                 |
      | status          | protecting                                           |
      +-----------------+------------------------------------------------------+

#. After a short time, verify successful creation of the checkpoint:

   .. code-block:: console

      $ karbor checkpoint-show cf56bd3e-97a7-4078-b6d5-f36246333fd9 c1112037-b19c-421a-83c9-dd209e785189
      +-----------------+-----------------------------------------------------------+
      | Property        | Value                                                     |
      +-----------------+-----------------------------------------------------------+
      | created_at      | 2017-03-27                                                |
      | extra_info      | None                                                      |
      | id              | c1112037-b19c-421a-83c9-dd209e785189                      |
      | project_id      | 690ccee85834425e973258252e0da888                          |
      | protection_plan | {                                                         |
      |                 |   "id": "81ac01b7-0a69-4b0b-8ef5-bd46a900c90a",           |
      |                 |   "name": "Plan1",                                        |
      |                 |   "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",  |
      |                 |   "resources": [                                          |
      |                 |     {                                                     |
      |                 |       "id": "286a43e9-3899-4983-965f-d8b1faef5e58",       |
      |                 |       "name": "Volume1",                                  |
      |                 |       "type": "OS::Cinder::Volume"                        |
      |                 |     }                                                     |
      |                 |   ]                                                       |
      |                 | }                                                         |
      | resource_graph  | [                                                         |
      |                 |   {                                                       |
      |                 |     "0x0": [                                              |
      |                 |       "OS::Cinder::Volume",                               |
      |                 |       "286a43e9-3899-4983-965f-d8b1faef5e58",             |
      |                 |       "Volume1"                                           |
      |                 |     ]                                                     |
      |                 |   },                                                      |
      |                 |   []                                                      |
      |                 | ]                                                         |
      | status          | available                                                 |
      +-----------------+-----------------------------------------------------------+

#. Create restore by checkpoint:

   .. code-block:: console

      $ karbor restore-create cf56bd3e-97a7-4078-b6d5-f36246333fd9 c1112037-b19c-421a-83c9-dd209e785189
      +------------------+--------------------------------------+
      | Property         | Value                                |
      +------------------+--------------------------------------+
      | checkpoint_id    | c1112037-b19c-421a-83c9-dd209e785189 |
      | id               | 2c9dea83-3e12-4fa1-80af-16f02b5738ef |
      | parameters       | {}                                   |
      | project_id       | 690ccee85834425e973258252e0da888     |
      | provider_id      | cf56bd3e-97a7-4078-b6d5-f36246333fd9 |
      | resources_reason | {}                                   |
      | resources_status | {}                                   |
      | restore_target   | None                                 |
      | status           | in_progress                          |
      +------------------+--------------------------------------+

#. After a short time, verify successful restore for the checkpoint:

   .. code-block:: console

      $ karbor restore-show 2c9dea83-3e12-4fa1-80af-16f02b5738ef
      +------------------+----------------------------------------------------------------------------+
      | Property         | Value                                                                      |
      +------------------+----------------------------------------------------------------------------+
      | checkpoint_id    | c1112037-b19c-421a-83c9-dd209e785189                                       |
      | id               | 2c9dea83-3e12-4fa1-80af-16f02b5738ef                                       |
      | parameters       | {}                                                                         |
      | project_id       | 690ccee85834425e973258252e0da888                                           |
      | provider_id      | cf56bd3e-97a7-4078-b6d5-f36246333fd9                                       |
      | resources_reason | {}                                                                         |
      | resources_status | {u'OS::Cinder::Volume#b0b2d98d-ec8a-498e-ad50-00a2240c76a2': u'available'} |
      | restore_target   | None                                                                       |
      | status           | success                                                                    |
      +------------------+----------------------------------------------------------------------------+

#. Delete the checkpoint.

   .. code-block:: console

      $ karbor checkpoint-delete cf56bd3e-97a7-4078-b6d5-f36246333fd9 c1112037-b19c-421a-83c9-dd209e785189
