..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Adding more protection parameters:retention period
==================================================

https://blueprints.launchpad.net/karbor/+spec/adding-more-protection-parameters-retention-period

Problem description
===================

Karbor supports the scheduled operation according the protection plan. As time
goes on, checkpoints are getting more and more. For example, if we create a
scheduled plan: protect resource every day, there are 7 checkpoints one week,
and about 30 checkpoints one month, etc. If we don't clean them manually, a
lot of checkpoint takes up our valuable storage resources.

In this specification we will introduce protection parameters:retention
period, max backup number. If the create time of the checkpoint is older
than retention period, we need to delete it, and if the checkpoints
number is more than max backup number, we need to delete the oldest one.

Use Cases
=========

Users create a scheduledoperation, in addition to setting the scheduling
period and plan, he can also set the retention period or (and) checkpoint
maximum number.

Proposed change
===============

Adding more protection parameters:retention period:
---------------------------------------------------
Add protection parameters in scheduledoperation: max_backups and
retention_duration. These parameters are used to control the number
of checkpoints to prevent excessive storage of resources due to
excessive checkpoints.

1. Delete checkpoints in the auto-scheduled mode:
Get max_backups and retention_duration from the scheduledoperation.

When creating the checkpoint is complete, get all the available checkpoints in the plan
and sort them according to created_at by desc, delete the older checkpoints
that exceeds the max_backups; and delete the checkpoints that their created_at
are older than the retention_duration.


protection parameters:retention schema:
---------------------------------------
::

   karbor scheduledoperation-create 'OS volumes retention protection' retention_protect 95e45924-49f4-4c12-b06f-5ec3c6245435
   "plan_id"="49dd4b84-a8f9-4592-b7d4-be1e37175af6","provider_id"="cf56bd3e-97a7-4078-b6d5-f36246333fd9","max_backups"=3,"retention_duration"=10

   +----------------------+-----------------------------------------------------------+
   | Property             | Value                                                     |
   +----------------------+-----------------------------------------------------------+
   | description          | None                                                      |
   | enabled              | True                                                      |
   | id                   | 2c39406d-209b-4cba-88b4-2d9c0826eb39                      |
   | name                 | OS volumes retention protection                           |
   | operation_definition | {                                                         |
   |                      |   "max_backups": "3",                                     |
   |                      |   "plan_id": "49dd4b84-a8f9-4592-b7d4-be1e37175af6",      |
   |                      |   "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",  |
   |                      |   "retention_duration": "10"                              |
   |                      | }                                                         |
   | operation_type       | retention_protect                                         |
   | trigger_id           | 95e45924-49f4-4c12-b06f-5ec3c6245435                      |
   +----------------------+-----------------------------------------------------------+

Note 1: max_backups:
For example, "max_backups=3" indicates maximum retention for 3 backups.
For example, "max_backups=10" indicates maximum retention for 10 backups.

Note 2: retention_duration's unit is day.
For example, "retention_duration=10" indicates maximum retention for 10 days.
For example, "retention_duration=14" indicates maximum retention for 2 weeks.


Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

None

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

Primary assignee:
gengchc2 <geng.changcai2@zte.com.cn>

Work Items
----------

*
* Delete checkpoint in the auto-scheduled mode: older checkpoints based on max_backups
  and retention_duration in the protection plan.
* Write tests

Dependencies
============

None


Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

None


References
==========

None
