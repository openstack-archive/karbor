..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Multi-tenant Isolation in Managing the Checkpoints
==================================================

https://blueprints.launchpad.net/karbor/+spec/checkpoint-tenant-isolation

Problem description
===================

In multi-tenants scenario, when a user lists all the checkpoints they
created, all the checkpoints in the bank will be returned. This is problematic
as there is nothing stopping one project to restore or delete another's data.
This means that users can use the update\restore mechanism to bypass other
security in OpenStack.

Use Cases
-----------

1. Provide a way to make the end users can only list the checkpoints that
created by themselves.
2. In cross site scenario, users can only do backup and restore between two
sites which have same project ids.
3. Admin can query all the checkpoints with parameter '--all-projects'.


Proposed Change
===============

Every project can see the checkpoints that are created by themselves.
Admin can see all the checkpoints in the bank.

Data model impact
-----------------
Adding `projects_id` to the data path of checkpoints in the bank 'indices'.

For example:
/checkpoints/f7702b65-6abe-4302-9542-4fb511ce5e14/ <- directory
/indices/by-date/2017-09-20/016fa93a9b204c49a12425574bdc5f4e/ <- by date
/indices/by-plan/08a5a407-6252-4514-9159-5f554af2acd0/016fa93a9b204c49a12425574bdc5f4e/ <- by plan
/indices/by-provider/cf56bd3e-97a7-4078-b6d5-f36246333fd9/016fa93a9b204c49a12425574bdc5f4e/ <- by provider

'016fa93a9b204c49a12425574bdc5f4e' is a project id.

REST API impact
---------------

None

Security impact
---------------

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

Dependencies
============

None

Testing
=======

None

Documentation Impact
====================

None

References
==========

None