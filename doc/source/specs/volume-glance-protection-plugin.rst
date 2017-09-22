..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Glance based cinder volume protection plugin
============================================

https://blueprints.launchpad.net/karbor/+spec/backup-volume-data-to-bank

Problem description
===================

Currently, karbor support using cinder backup, cinder snapshot and freezer
plugins to do cinder volume backup. These plugins all store the backup metadata
to the bank but not the volume backup data.

In the use case of cross site, we need to do cinder volume backup and restore
cross different sites (with different cinder/nova/glance service endpoints),
this requires karbor to save the volume data in an independent storage media
(bank), so that we can do backup in one site and do restore in another site
that the two sites use the same volume backup data in one bank.

Obviously the cinder volume protection plugins in karbor can not satisfy the
cross site needs now. So we should introduce a new volume protection plugin
which can save volume data to karbor's bank, like image protection plugin.
Backup cinder volume through glance may be a valid choice.

Use Cases
=========

As explained, users who want to do cross site backup and restore of cinder
volumes.

Proposed change
===============

Volume glance protection plugin
-------------------------------

Add a new volume protection plugin which do the backup and restore of cinder
volumes by glance service. Volume data would be stored in the bank as chunks
like what image protection plugin do.

Steps of protect operation:
1. Create a temporary snapshot to the volume you want to backup
2. Create a temporary volume based on the snapshot in step 1
3. Create a temporary glance image of the temporary volume
4. Download the temporary image and save it to karbor bank
5. Clean all the temporary resources in step 1 to 4
6. Save the backup metadata to bank

Steps of restore operation:
1. Create an image with the volume data in bank
2. Create a volume with the created image in step 1
3. Wait for the volume status being available
4. Clean the created image in step 1

Steps in delete operation:
1. List and delete the objects (volume data and metadata) in bank.

Volume glance protection plugin schema:
---------------------------------------

::

    OPTIONS_SCHEMA = {
        "title": "Volume Glance Protection Options",
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
        "title": "Volume Glance Protection Restore",
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

None.

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

This plugin may be slower than cinder backup and cinder snapshot plugin.

Other deployer impact
---------------------

Add the volume by glance protection plugin endpoint to setup.cfg.
Add the volume by glance protection plugin configuration to provider file.

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

* Write volume by glance protection plugin
* Write tests

Dependencies
============

None


Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

Add a usage example about volume by glance protection.


References
==========

None
