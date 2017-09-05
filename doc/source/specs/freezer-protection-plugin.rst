..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================
Freezer protection plugin
==========================

https://blueprints.launchpad.net/karbor/+spec/freezer-protection-plugin

Problem description
===================

Currently, Karbor provides some default protection plugins to protect nova instances
or cinder volumes etc. We should increase support for more protection plugins to satisfy
user's needs more flexibly in different scenarios.

Freezer is a distributed backup restore and disaster recovery as a service platform.
Now it supports the backup of nova instances and cinder volumes which are managed by
OpenStack environment. At the same time, Freezer can backup the resources to the storage
medias outside the OpenStack environment or different storage medias in a backup. So it
will be useful to introduce Freezer as a protection plugin for Karbor. With Freezer, we
will have more strategies to protect our cloud resources.

Use Cases
=========

Users who want to use Freezer as a backup restore service for their OpenStack environment.

Proposed change
===============

Freezer protection plugin
-------------------------

Freezer protection plugin which supports project, server, volume, image and network
resource types need be implemented.

For project, freezer plugin will backup all the resources (tenant backup implemented in
Freezer).

For server, freezer plugin will backup a specify nova instance (if the instance was image
boot, Freezer will backup the image and network; if the instance was volume boot, Freezer
will backup the system volume).

For volume, freezer plugin will backup a specify cinder volume.

For image and network, freezer plugin will do nothing as it do not support backup these
two types of resources independently.

A new protection plugin about Freezer need be implemented.

1. Protect Operation:

    In main hook of this operation, freezer client will be called to create a freezer job
    which contains backup actions to do the backup of protectable resources.
    After the backup, the freezer job and its actions will be deleted.

2. Restore Operation:

    In main hook of this operation, freezer client will be called to create a freezer job
    which contains restore actions to do the restore of protectable resources.
    After the restore, the freezer job and its actions will be deleted.

3. Delete Operation:

    In main hook of this operation, freezer client will be called to create a freezer job
    which contains admin actions to delete of backup of the resources.
    After the deletion, the freezer job and its actions will be deleted.

Freezer protection plugin schema:
-------------------------------------------------

::

    OPTIONS_SCHEMA = {
        "title": "Freezer Protection Options",
        "type": "object",
        "properties": {
            "backup_name": {
                "type": "string",
                "title": "Backup Name",
                "description": "The name of the backup.",
                "default": None
            },
            "description": {
                "type": "string",
                "title": "Description",
                "description": "The description of the backup."
            }
        },
        "required": ["backup_name"]
    }

    RESTORE_SCHEMA = {
        "title": "Freezer Protection Restore",
        "type": "object",
        "properties": {
            "restore_name": {
                "type": "string",
                "title": "Restore Resource Name",
                "description": "The name of the restore resource ",
                "default": None
            },
        },
        "required": ["restore_name"]
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

Add freezer protection plugin endpoint to setup.cfg.
Add freezer protection plugin configuration to provider file.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
Pengju Jiao <jiaopengju@cmss.chinamobile.com>

Work Items
----------

* Write freezer protection plugin
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
