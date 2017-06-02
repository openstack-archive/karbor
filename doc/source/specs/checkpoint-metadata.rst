..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
API for custom checkpoint meta-data
==========================================

https://blueprints.launchpad.net/cinder/+spec/custom-checkpoint-metadata

Problem description
===================

Currently when creating a checkpoint. The only place to add custom information
apart from the name is in the description field. This means that tools that
create checkpoints needs to use this user visible space for their own metadata.

User data can only be set during creation and is read-only from that point on.

Use Cases
=========

A tool creates a checkpoint and want's to add information related to the tools
functions. For example a tool that creates checkpoints due to specific external
events would like to add the event_id of the event that triggered the
checkpoint creation.

Proposed change
===============

When creating a checkpoint a new field would be available called
``extra-info``.
This field must be a map in the format of::

        {
                "key": "value",
        }

Keys and values *must* both be strings. Keys that are officially recognized
will be in the format of ``karbor-<key-name>`` for example
``karbor-created-by``.

Anything that is not officially defined *should* use the
prefix: ``x-<application>--<key-name>``.
For example, ``x-trigger-master--trigger-id``

Alternatives
------------

Do nothing, this is not a mission critical feature.

Data model impact
-----------------

New field for a checkpoint called ``extra-info``.

REST API impact
---------------

New optional body attribute when creating a new checkpoint::

    POST/v1/{tenant_id}/checkpoint

    {
        ...
        "extra-info": {
                "karbor-created-by": "operation-engine"
        }
    }

Security impact
---------------

We need to make sure the number of entries and their size is within bounds
to prevent any attacks.

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
