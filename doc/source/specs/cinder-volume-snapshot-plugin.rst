..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================================
Cinder volume snapshot protection plugin
=========================================

https://blueprints.launchpad.net/karbor/+spec/cinder-volume-snapshot-plugin

Problem description
===================

Now there is a cinder default volume protection plugin implemented using the backup
feature of cinder volume in karbor. A new cinder protection plugin will be introduced to
karbor, it will use the snapshot feature of cinder to protect the volume.


Use Cases
=========

User creates a volume in cinder, and mounts it to the server. Then the volume
is used for saving lots of data by user. To avoid the loss of data, the user
want to protect the volume by making periodic snapshots of this volume.
If the user want to restore the volume, he can create a new volume from this
snapshot.

Proposed change
===============

Cinder volume snapshot protection plugin:
-----------------------------------------
A new snapshot protection plugin about Cinder volume need be implemented.

1. Protect Operation:
The 'create' method of cinderclient's SnapshotManager will be called in the main hook
of this operation to make a snapshot of the volume. A snapshot of the resource
volume will be created.

2. Restore Operation:
The 'create' method of cinderclient's VolumeManager will be called in the main hook of
this operation to create a new volume from the giving snapshot.
A new volume from the snapshot will be created.

3. Delete Operation:
The volume snapshot will be deleted.
The 'delete' method of cinderclient's SnapshotManager will be called in the main hook
of this operation to delete the volume snapshot.

Cinder volume snapshot protection plugin schema:
------------------------------------------------

OPTIONS_SCHEMA = {
    "title": "Volume Snapshot Protection Options",
    "type": "object",
    "properties": {
        "snapshot_name": {
            "type": "string",
            "title": "Snapshot Name",
            "description": "The name of the volume snapshot."
        },
        "description": {
            "type": "string",
            "title": "Description",
            "description": "The description of the volume snapshot."
        },
        "force": {
            "type": "boolean",
            "title": "Force",
            "description": "If force is True, create a snapshot even if the volume is attached to an instance.",
            "default": False
        }
    },
    "required": ["snapshot_name", "description", "force"]
}

RESTORE_SCHEMA = {
    "title": "Volume Protection Restore",
    "type": "object",
    "properties": {
        "restore_name": {
            "type": "string",
            "title": "Restore Name",
            "description": "The name of the restored volume.",
            "default": None
        },
        "restore_description": {
            "type": "string",
            "title": "Restore Description",
            "description": "The description of the restored volume.",
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

Add this volume snapshot plugin to the entry_points section of setup.cfg.
Add this volume snapshot plugin configuration to provider file.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* Write volume snapshot protection plugin
* Write tests
* Add a usage example about volume snapshot protection

Dependencies
============

None


Testing
=======

Unit tests in Karbor .


Documentation Impact
====================

Add a usage example about volume snapshot protection.


References
==========

None
