..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================
Add Quotas to Karbor
====================

https://blueprints.launchpad.net/karbor/+spec/support-quotas-in-karbor

Problem description
===================

To prevent system capacities from being exhausted without notification, users can
set up quotas. Quotas are operational limits.
For example, the number of gigabytes allowed for each project can be controlled so
that cloud resources are optimized in Block Storage service(Cinder)[1] . Quotas can
be enforced at the project level. Nova uses a quota system for setting limits on
resources such as number of instances or amount of CPU that a specific project or
user can use. [2]

A quotas system will be introduced to Karbor for setting limits on resources such
as the amount of gigabytes about backup data that a specific project can use.

Use Cases
=========

User can set limits on resources such as the amount of gigabytes about backup data
via a new quotas RESTful API.


Proposed change
===============
1. Two data modules about quotas will be introduced to karbor.

   The data module 'quotas' is used for saving the hard limit number of the resources
   that a specific project can use.
   The data module 'quota_usages' is used for saving the in use number and reserved
   number of the resources that belong to a specific project.


2. Add the quotas API controller for the Karbor API.

   Implement the 'update' method of quotas API controller.
   Implement the 'show' method of quotas API controller.
   Implement the 'index' method of quotas API controller.

2. The resources need to limit.

   QUOTAS_PLAN_CAPACITY = 'quota_plans'

   QUOTAS_PLAN_CAPACITY: The maximum number of plan.

3. Init the default limit number of the resources about quotas data module.

   The default limit number of the resources should be inited in the data module
   table 'quotas' when the karbor api service start to run.
   The default limit number of the resources can be set from the value of configurations.
   The config 'quota_plans' need be added.


4. Update the reserved and in use number of the resources quota usages.

   When a resource is requested, the specific quota about this resource is checked first.
   If this check passes, the reserved number of this resource in data module 'quota_usages'
   need be updated first according to requested resource number. If the resource is
   created successfully, the in use number of the resources quota need be updated. At the
   same time, the reserved number of this resource should be subtracted.


Alternatives
------------

None

Data model impact
-----------------
1. quotas

+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | varchar(36)  | NO   | PRI | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| project_id              | varchar(255) | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| resource                | varchar(255) | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| hard_limit              | Interger     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| created_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| updated_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| deleted_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+

2. quota_usages

+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | varchar(36)  | NO   | PRI | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| project_id              | varchar(255) | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| resource                | varchar(255) | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| in_use                  | Interger     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| reserved                | Interger     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| created_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| updated_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| deleted_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+

REST API impact
---------------

1. Update quotas  API, admin only.
The request JSON when updating a quota::

    **post** : /v1/{project_id}/quotas/{user_project_id}
    ```json
    {
      "quota":
        {
          "plans": 100
        }
    }


The response JSON when updating a quota::

    ```json
    {
        "quota":{
          "plans": 100
        }
    }



2. Show quota API. Admin can query aother projects' quota.
The response JSON when showing a quota::

    **get** : /v1/{project_id}/quotas/{user_project_id}
    ```json
    {
        {
            "quota": {
                "plans": 100,
                "id": "73f74f90a1754bd7ad658afb3272323f"
            }
        }
    }


3. Delete quota API. admin only.
The response JSON when deleting a quota::

    **delete** : /v1/{project_id}/quotas/{user_project_id}

4. Show the detail of quota API. Admin can query aother projects' quota.
The response JSON when showing a quota::

    **get** : /v1/{project_id}/quotas/{user_project_id}/detail
    ```json
    {
        "quota": {
            "plans": {
                "reserved": 0,
                "limit": 100,
                "in_use": 1
            },
            "id": "73f74f90a1754bd7ad658afb3272323f"
        }
    }

5. Show the default of quota API. Admin can query aother projects' quota.
The response JSON when showing a quota::

    **get** : /v1/{project_id}/quotas/{user_project_id}/defaults
    ```json
    {
        "quota": {
            "plans": 50,
            "id": "73f74f90a1754bd7ad658afb3272323f"
        }
    }


6. Update quota class  API, admin only.
The request JSON when updating a quota class::

    **post** : /v1/{project_id}/quota_classes/{class_name}
    ```json
    {
        "quota_class": {
            "plans": 120
        }
    }


The response JSON when updating a quota class::

    ```json
    {
        "quota_class": {
            "plans": 120
        }
    }


7. Show quota class API.
The response JSON when showing a quota class::

    **get** : /v1/{project_id}/quota_classes/{class_name}
    ```json
    {
        "quota_class": {
            "plans": 120,
            "id": "default"
        }
    }


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* Add a new RESTful API about quotas
* Add database data module of quotas
* Add quotas API to karbor client

Dependencies
============



Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

None

References
==========

[1] https://docs.openstack.org/horizon/latest/admin/set-quotas.html

[2] https://docs.openstack.org/nova/latest/user/quotas.html

