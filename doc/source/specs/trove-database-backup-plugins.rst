..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================================
Trove database instance protectable and protection plugins
==========================================================

https://blueprints.launchpad.net/karbor/+spec/trove-database-proection-plugin

Problem description
===================

The database instance managed by Trove can not be protected by Karbor now. Currently,
Trove as a Database service allows the user to quickly and easily use database features
without the burden of handling complex administrative tasks.

The users can use Database service (Trove) to backup a database and store the backup
artifact in the Object Storage service. Later on, if the original database is damaged,
users can use the backup artifact to restore the database. The restore process creates
a database instance.

So the backup feature of database instance can be introduced to karbor by making a
protection plugin for the database instance.


Use Cases
=========

User creates the database instance in Trove. Then the database instance is used for
saving lots of relational and non-relational data by user. To avoid the loss of these
data, the user want to protect them by making periodic backup of this database instance.
If the user want to restore the database instance, he can create a new database instance
from a backup.

Proposed change
===============

Trove database instance protectable plugin:
-------------------------------------------
A new protectable plugin about Trove database instance need be implemented.
The type of resource database instance is "OS::Trove::Instance". It will be added to the constant
RESOURCE_TYPES in karbor.


1. The parent resource types: PROJECT_RESOURCE_TYPE

2. list the resources:

   This interface of plugin will call the 'list' method of Instances manager in troveclient.

3. show the resource:

   This interface of plugin will call the 'get' method of Instances manager in troveclient.
   The parameter is a database instance id.

4. get dependent resources:

   The parameter parent_resource is a project, this interface of plugin will return the
   database instance in this project.


Trove database instance protection plugin
-----------------------------------------
A new protection plugin about Trove database instance need be implemented.

1. Protect Operation:

   The 'create' method of Backups manager will be called in the main hook
   of this operation to make a backup of the database instance.

2. Restore Operation:

   The 'create' method of Instances manager
   will be called in the main hook of this operation to create a new database instance from
   the giving backup.

3. Delete Operation:

   The database instance backup will be deleted.
   The 'delete' method of Backups manager will be called in the main hook
   of this operation to delete the database instance backup.

Trove database instance protection plugin schema:
-------------------------------------------------

::

    OPTIONS_SCHEMA = {
        "title": "Database Instance Protection Options",
        "type": "object",
        "properties": {
            "backup_name": {
                "type": "string",
                "title": "Backup Name",
                "description": "The name of the database instance backup."
            },
            "description": {
                "type": "string",
                "title": "Description",
                "description": "The description of the database instance backup."
            }
        },
        "required": ["backup_name", "description"]
    }

    RESTORE_SCHEMA = {
        "title": "Database Instance Protection Restore",
        "type": "object",
        "properties": {
            "restore_name": {
                "type": "string",
                "title": "Restore Name",
                "description": "The name of the restored database instance.",
                "default": None
            },
            "restore_description": {
                "type": "string",
                "title": "Restore Description",
                "description": "The description of the restored database instance.",
                "default": None
            }
        }
    }


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

Add the database instance protection plugin endpoint to setup.cfg.
Add the database instance protection plugin configuration to provider file.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* Write database instance backup protectable plugin
* Write database instance backup protection plugin
* Write tests
* Add a usage example about database instance protection

Dependencies
============

None


Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

Add a usage example about database instance protection.


References
==========

None
