..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============
API Service
============

https://review.openstack.org/#/c/266338/

The APIs expose Application Data Protection services to the Karbor user.

The purpose of the services is to maximize flexibility and accommodate
for (hopefully) any kind of protection for any type of resource, whether
it is a basic OpenStack resource (such as a VM, Volume, Image, etc.) or
some ancillary resource within an application system that is not managed
in OpenStack (such as a hardware device, an external database, etc.).



==========================
WSGI Resources Controller
==========================

The WSGI Controller handles incoming web requests that are dispatched
from the WSGI application APIRouter.

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/api-service-class-diagram.png

From the module class graph, api service basically have following
resources Controller:

Provider Controller
-----------------------
Enables the Karbor user to list available providers and get parameters and
result schema super-set for all plugins of a specific Provider.


Checkpoint Controller
-----------------------
Enables the Karbor user to access and manage the checkpoints stored
in the protection provider.


Protectable Controller
-----------------------

Enables the Karbor user to access information about which resource types
are protectable (i.e. can be protected by Karbor).
In addition, enables the user to get additional information on each
resource type, such as a list of actual instances and their dependencies.

Plan Controller
-----------------------

This API enables the Karbor user to access the protection Plan registry
and do the following operations:
-  Plan CRUD.
-  List Plans.
-  Starting and suspending of plans.


Scheduled Operation Controller
--------------------------

This API enables the Karbor user to manage Scheduled Operations:

-  Operation CRUD.
-  List Operations.

Trigger Controller
--------------------------

This API enables the Karbor user to manage Triggers:
A trigger only can be deleted when it isn't used in any of the
scheduled operation.
-  Trigger CRUD.
-  List Triggers.


Restore Controller
---------------------------

This API enables the Karbor user restore a checkpoint on to a restore target:

-  Create restored system from a checkpoint.


====================================
API Service Data base tables
====================================



time_triggers and scheduled_operations database tables are the same as
tables in the operation engine design.

1. plans
+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | varchar(36)  | NO   | PRI | NULL    |       |
| name                    | varchar(255) | NO   |     | NULL    |       |
| provider_id             | varchar(36)  | NO   |     | NULL    |       |
| project_id              | varchar(255) | NO   |     | NULL    |       |
| status                  | varchar(64)  | NO   |     | NULL    |       |
| created_at              | Datetime     | YES  |     | NULL    |       |
| updated_at              | Datetime     | YES  |     | NULL    |       |
| deleted_at              | Datetime     | YES  |     | NULL    |       |
| deleted                 | Boolean      | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+

2. resources
+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | Integer      | NO   | PRI | NULL    |       |
| plan_id                 | varchar(255) | NO   | FOR | NULL    |       |
| resource_id             | varchar(36)  | NO   |     | NULL    |       |
| resource_type           | varchar(64)  | NO   |     | NULL    |       |
| created_at              | Datetime     | YES  |     | NULL    |       |
| updated_at              | Datetime     | YES  |     | NULL    |       |
| deleted_at              | Datetime     | YES  |     | NULL    |       |
| deleted                 | Boolean      | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+

3. restores
+-----------------+--------------+------+-----+---------+-------+
| Field           | Type         | Null | Key | Default | Extra |
+-----------------+--------------+------+-----+---------+-------+
| id              | varchar(36)  | NO   | PRI | NULL    |       |
| project_id      | varchar(255) | NO   |     | NULL    |       |
| provider_id     | varchar(36)  | NO   |     | NULL    |       |
| checkpoint_id   | varchar(36)  | NO   |     | NULL    |       |
| restore_target  | varchar(255) | NO   |     | NULL    |       |
| parameters      | varchar(255) | NO   |     | NULL    |       |
| status          | varchar(64)  | NO   |     | NULL    |       |
| created_at      | Datetime     | YES  |     | NULL    |       |
| updated_at      | Datetime     | YES  |     | NULL    |       |
| deleted_at      | Datetime     | YES  |     | NULL    |       |
| deleted         | Boolean      | NO   |     | NULL    |       |
+-----------------+--------------+------+-----+---------+-------+

4. triggers
+--------------------+--------------+------+-----+---------+-------+
| Field              | Type         | Null | Key | Default | Extra |
+--------------------+--------------+------+-----+---------+-------+
| id                 | varchar(36)  | NO   | PRI | NULL    |       |
| name               | varchar(255) | NO   |     | NULL    |       |
| project_id         | varchar(255) | NO   |     | NULL    |       |
| type               | varchar(64)  | NO   |     | NULL    |       |
| properties         | TEXT         | NO   |     | NULL    |       |
| created_at         | Datetime     | YES  |     | NULL    |       |
| updated_at         | Datetime     | YES  |     | NULL    |       |
| deleted_at         | Datetime     | YES  |     | NULL    |       |
| deleted            | Boolean      | NO   |     | NULL    |       |
+--------------------+--------------+------+-----+---------+-------+

5. scheduled_operations
+----------------------+--------------+------+-----+---------+-------+
| Field                | Type         | Null | Key | Default | Extra |
+----------------------+--------------+------+-----+---------+-------+
| id                   | varchar(36)  | NO   | PRI | NULL    |       |
| name                 | varchar(255) | NO   |     | NULL    |       |
| operation_type       | varchar(64)  | NO   |     | NULL    |       |
| project_id           | varchar(255) | NO   |     | NULL    |       |
| trigger_id           | varchar(36)  | NO   |     | NULL    |       |
| operation_definition | TEXT         | NO   |     | NULL    |       |
| created_at           | Datetime     | YES  |     | NULL    |       |
| updated_at           | Datetime     | YES  |     | NULL    |       |
| deleted_at           | Datetime     | YES  |     | NULL    |       |
| deleted              | Boolean      | NO   |     | NULL    |       |
+----------------------+--------------+------+-----+---------+-------+

5. services
+----------------------+--------------+------+-----+---------+-------+
| Field                | Type         | Null | Key | Default | Extra |
+----------------------+--------------+------+-----+---------+-------+
| id                   | Integer      | NO   | PRI | NULL    |       |
| host                 | varchar(255) | NO   |     | NULL    |       |
| binary               | varchar(255) | NO   |     | NULL    |       |
| topic                | varchar(255) | NO   |     | NULL    |       |
| report_count         | Integer      | NO   |     | NULL    |       |
| disabled             | Boolean      | NO   |     | NULL    |       |
| disabled_reason      | varchar(255) | NO   |     | NULL    |       |
| modified_at          | Datetime     | NO   |     | NULL    |       |
| rpc_current_version  | varchar(36)  | NO   |     | NULL    |       |
| rpc_available_version| varchar(36)  | NO   |     | NULL    |       |
| created_at           | Datetime     | YES  |     | NULL    |       |
| updated_at           | Datetime     | YES  |     | NULL    |       |
| deleted_at           | Datetime     | YES  |     | NULL    |       |
| deleted              | Boolean      | NO   |     | NULL    |       |
+--------------------+--------------+------+-----+---------+-------+
