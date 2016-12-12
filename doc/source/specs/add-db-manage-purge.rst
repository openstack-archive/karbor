..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Karbor db purge utility
==========================================

https://blueprints.launchpad.net/karbor/+spec/clean-deleted-data-in-db

This spec adds the ability to sanely and safely purge deleted rows from
the karbor database for all relevant tables. Presently, we keep all deleted
rows. I believe this is unmaintainable as we move towards more upgradable
releases. Today, the operators depend on manual DB queries to delete this
data, but this exposes the DB to human errors.

The goal is to have this be an extension to the `karbor-manage db` command.
Similar specs are being submitted to all the various projects(Cinder, Glance)
that touch a database.

Problem description
===================

Very long lived OpenStack installations will carry around database rows
for years and years. This brings following problems:

* If deleted data is kept in the DB, the number of rows can grow very large
  taking up the disk space of nodes. Larger disk space means more worry
  for disaster recovery, long running non-differential backups, etc.

* Large number of deleted rows also means, an admin or authorized owner
  querying for the corresponding rows will get 5xx responses timing out
  on the DB, eventually slowing down other queries and API performance.

* DB upgradeability is a big challenge if the older data style are less
  or inconsistent with the latest formats.

To date, there is no "mechanism" to programmatically purge the deleted
data.

Proposed change
===============

The proposal is to add a "purge" method to DbCommands in
karbor/karbor/cmd/manage.py. This will take a number of days argument,
and use that for a data_sub match Like.
Like::

  DELETE FROM plans
    WHERE deleted != 0 AND deleted_at > data_sub(NOW()...)

Alternatives
------------

Today, this can be accomplished manually with SQL commands, or via script.

Data model impact
-----------------

None, all tables presently include a "deleted_at" column.

REST API impact
---------------

None, this would be run from karbor-manage

CLI impact
----------

A new karbor-manage command will be added:

   karbor-manage db purge <age_in_days>

Security impact
---------------

None, This only touches already deleted rows.

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

This has the potential to improve performance for very large databases.
Very long-lived installations can suffer from inefficient operations
on large tables.
This would have negative DB performance impact while the purge is running.

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
  chenying

Work Items
----------

Implement 'db purge' command.
Add tests to confirm functionality
Add documentation of feature

Dependencies
============

None

Testing
=======

The test will be written as such. Three rows will be inserted into a test db.
Two will be "deleted=1", one will be "deleted=0"
One of the deleted rows will have "deleted_at" be NOW(), the other will be
"deleted_at" a few days ago, lets say 10. The test will call the new
function with the argument of "7", to verify that only the row that was
deleted at 10 days ago will be purged. The two other rows should remain.

Documentation Impact
====================

Documentation of this feature will be added to the admin guide and
developer reference.

References
==========

This is already discussed and accepted in other OpenStack components,
such as Glance [1] and Cinder [2].

[1] https://specs.openstack.org/openstack/glance-specs/specs/mitaka/database-purge.html
[2] https://specs.openstack.org/openstack/cinder-specs/specs/kilo/database-purge.html