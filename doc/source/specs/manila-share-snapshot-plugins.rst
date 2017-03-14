..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Manila share protectable and protection plugins
===================================================

https://blueprints.launchpad.net/karbor/+spec/manila-share-proection-plugin

Problem description
===================

The shares managed by Manila can not be protected by Karbor now. Currently, Manila allows
the user to create snapshots of the share. So the protection feature of share can be
introduced to karbor by making a snapshot of the share.


Use Cases
=========

User creates the share in Manila, and mounts it to the server. Then the share
is used for saving lots of files data by user. To avoid the loss of files data,the user
want to protect the shares by making periodic snapshots of this share.
If the user want to restore the share, he can create a new share from a snapshot.

Proposed change
===============

Manila share protectable plugin:
--------------------------------
A new protectable plugin about Manila share need be implemented.
The type of resource share is "OS::Manila::Share". It will be added to the constant
RESOURCE_TYPES in karbor.


1. The parent resource types:
PROJECT_RESOURCE_TYPE.

2. list the resources:
This interface of plugin will call the 'list' method of ShareManager in manilaclient.

3. show the resource:
This interface of plugin will call the 'get' method of ShareManager in manilaclient.
The parameter is a share id.

4. get dependent resources:
The parameter parent_resource is a project, this interface of plugin will return the
shares in this project.


Manila share protection plugin
--------------------------------
A new protection plugin about Manila share need be implemented.

1. Protect Operation:
The 'create' method of ShareSnapshotManager will be called in the main hook
of this operation to make a snapshot of the share.

2. Restore Operation:
The 'create' method of ShareManager
will be called in the main hook of this operation to create a new share from
the giving snapshot.

3. Delete Operation:
The share snapshot will be deleted.
The 'delete' method of ShareSnapshotManager will be called in the main hook
of this operation to delete the share snapshot.

Manila share protection plugin schema:
--------------------------------------

OPTIONS_SCHEMA = {
    "title": "Share Protection Options",
    "type": "object",
    "properties": {
        "snapshot_name": {
            "type": "string",
            "title": "Snapshot Name",
            "description": "The name of the snapshot."
        },
        "description": {
            "type": "string",
            "title": "Description",
            "description": "The description of the share snapshot."
        },
        "force": {
            "type": "boolean",
            "title": "Force",
            "description": "Optional flag to indicate whether to snapshot a share even if it's busy.",
            "default": False
        }
    },
    "required": ["snapshot_name", "description", "force"]
}

RESTORE_SCHEMA = {
    "title": "Share Protection Restore",
    "type": "object",
    "properties": {
        "share_id": {
            "type": "string",
            "title": "Share ID",
            "description": "The target share ID to restore to."
        },
        "restore_name": {
            "type": "string",
            "title": "Restore Name",
            "description": "The name of the restored share.",
            "default": None
        },
        "restore_description": {
            "type": "string",
            "title": "Restore Description",
            "description": "The description of the restored share.",
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

Add the share protection plugin endpoint to setup.cfg.
Add the share protection plugin configuration to provider file.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* Write share snapshot protectable plugin
* Write share snapshot protection plugin
* Write tests
* Add a usage example about share protection

Dependencies
============

None


Testing
=======

Unit tests in Karbor .


Documentation Impact
====================

Add a usage example about share protection.


References
==========

None
