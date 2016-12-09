..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Checkpoint scheduled clean
==========================================

https://blueprints.launchpad.net/karbor/+spec/checkpoint-scheduled-clean

Problem description
===================

Karbor provides Operation Engine Service to support the scheduled operation for
a protection plan. The scheduled operations will create lots of checkpoints as
the triggers define the rules. The checkpoints will be created every day or
every week or every month. Currently Karbor has no automatic clean feature and
policy for the end user.

Use Cases
=========

With more and more checkpoints created in the Bank, the end users need more
and more storage capacity, and some checkpoints are not meaningful and
necessary for the end users. The checkpoint scheduled clean feature is
necessary to satisfy the end user's requirement.

Proposed change
===============

Karbor provides the end users some settings including ``max_backups`` and
``retention_duration`` for the scheduled operation. Karbor could clean the
deprecated checkpoints which are created by the scheduled operation
automatically as the end users define.

#. **max_backups**: the max amount of checkpoints.which are created by the
   scheduled operation. e.g. 10.
#. **retention_duration**: the retention time of checkpoints which are created
   by the scheduled operation. e.g. 20 weeks.

Karbor provides the default values for these two settings. The default value is
-1, which means Karbor will not clean the checkpoints by default. When the end
users launch a scheduled operation, they can input the values of these two
settings and invoke the scheduled operation RESTful API.

Meanwhile a database table called **checkpoint_records** will be created to
store the checkpoints which are created by the **scheduled protect** or
**protect now**. This table's data will keep a real-time mapping to the
checkpoints in the Bank.

+--------------------+--------------+------+-----+---------+----------------+
| Field              | Type         | Null | Key | Default |      Extra     |
+====================+==============+======+=====+=========+================+
| created_at         | datetime     | YES  |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| updated_at         | datetime     | YES  |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| deleted_at         | datetime     | YES  |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| deleted            | tinyint(1)   | NO   |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| id                 | uuid         | NO   | PRI | NULL    | auto_increment |
+--------------------+--------------+------+-----+---------+----------------+
| project_id         | varchar(36)  | NO   |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| checkpoint_id      | varchar(36)  | NO   |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| checkpoint_status  | varchar(36)  | NO   |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| provider_id        | varchar(36)  | NO   |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| plan_id            | varchar(36)  | NO   |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| operation_id       | varchar(36)  | YES  |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| create_by          | varchar(36)  | YES  |     | NULL    |                |
+--------------------+--------------+------+-----+---------+----------------+
| extend_info        | Text         | YES  |     | NULL    |  detail info   |
+--------------------+--------------+------+-----+---------+----------------+

When the Operation Engine Service triggers an operation, and the operation
will invoke the REST API to create a checkpoint, and the API Service will
launch a checkpoint creation workflow and save the checkpoint information into
database table called **checkpoint_records**. If the end users delete a
checkpoint, the API Service will launch a checkpoint deletion workflow and
delete this checkpoint information from the database.

When the operation is triggered in the Operation Engine Service, the operation
could get the values of ``max_backups`` and ``retention_duration`` from the
scheduled operation, and then the operation will judge these two values to
confirm whether it will invoke the REST API to clean the deprecated
checkpoints.

Alternatives
------------

Do nothing, this is not a mission critical feature.

Data model impact
-----------------

Add two key-values in the operation_definition of scheduled protect operation.
These two optional key-values are called ``max_backups`` and
``retention_duration``.

REST API impact
---------------

New optional body attribute when creating a scheduled operation::

    **POST** : /v1/{project_id}/scheduled_operations
    ```json
    {
        ...
        "operation_definition": {
            ...
            "max_backups": 10,
            "retention_duration": 20
        }
    }
    ```

Security impact
---------------

We need to make sure the two values are within bounds to prevent any attacks.
The bounds will be defined in the local config.

Notifications impact
--------------------

None

Other end user impact
---------------------

The new API will be exposed to users via the python-karborclient.

Performance Impact
------------------

Filtering the results might cause a slight performance impact for the REST
API.

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

* Write API
* Add to Karbor client
* Write tests
* Add documentation

Dependencies
============

None


Testing
=======

Unit tests in Karbor and the python-karborclient.


Documentation Impact
====================

New docs to explain how to use the API.


References
==========

None
