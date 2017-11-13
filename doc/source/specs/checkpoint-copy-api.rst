..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==================================================
Add checkpoint copy API about protection to Karbor
==================================================

https://blueprints.launchpad.net/karbor/+spec/support-copy-the-checkpoint-api

Problem description
===================

Use case: Karbor + the backup software plugins + storage back-ends

All the backup softwares have multifarious storage back-ends. These storage back-ends of it
may be the traditional storage array devices or the object storage(Swift/S3). The backup
softwares can manage and choose to use the storage back-ends.

To prevent backup data about the resources in OpenStack loss, the backup software will deploy
several storage back-ends in different Availability Zones or Regions for one cloud environment.
By default, the resources in one plan are backed up when user creating a checkpoint in Karbor.
The backup data of these resources about this checkpoint will be stored in the main storage
back-ends of the backup software. The could provider want to expose the copy capacity of the
backup software, so that the resources backup data can be copied from main storage back-end
to another back-end in different az or region. Even the backup data of these resources in main
storage back-end are damaged for some reasons, the resources in this plan also can be restored
from another storage back-end of the backup software.


Use Cases
=========

User want to copy the backup copies in one checkpoint from one back-end to another storage
back-end of the backup software via a new RESTful API before he restoring new resources from
this checkpoint.
The backup softwares vendors also need Karbor protection plugins to support a copy
operation about the resource backup data, so that they can expose the copy of backup
data to users from Karbor protection service.


Proposed change
===============
1. Add the copy API controller for the Karbor API.
   Implement the 'create' method of copy API controller.
   In this API controller, all the uncopied checkpoint created from this plan
   will be copied.

2. The copy status of checkpoint resources.
   CHECKPOINT_STATUS_WAIT_COPYING = 'wait_copying'
   CHECKPOINT_STATUS_COPYING = 'copying'
   CHECKPOINT_STATUS_COPY_FINISHED = 'finished'

3. Add a new copy operation for protection plugins

   Add a new CopyOperation for protection plugins. The copy operation for the plugin is optional,
   most of time the backup softwares plugins can implement a copy operation.
   For example, the CopyOperation of backup software volume protection plugin, the backup data
   can be copied from main storage back-end to another back-end in different az or region.


4. Add operation_log for copy API.
   Add a new copy flow in the protection service of Karbor.
   If the CopyOperation about the checkpoint has not run successfully in the
   copy flow, the status of operation_log object will be set to 'error' in the
   'revert' method of InitiateCopyTask. The status of operation_log object will
   be set to 'success' in the CompleteCopyTask.


Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

1. Create copy  API
The request JSON when creating a copy::

    **post** : /v1/{project_id}/providers/{provider_id}/checkpoints/action
    ```json
    {
      "copy": [
        {
          "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
          "plan_id": "3523a271-68aa-42f5-b9ba-56e5200a2ebb",
          "parameters": {
            "OS::Cinder::Volume": {
            },
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
            }
          }
        }
      ]
    }


The response JSON when Creating a copy::

    ```json
    {
        "copy":{
          "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
          "project_id": "e486a2f49695423ca9c47e589b948108",
          "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
          "plan_id": "3523a271-68aa-42f5-b9ba-56e5200a2ebb",
          "parameters": {
            "OS::Cinder::Volume": {
            },
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
            }
          },
          "status": "error"
        }
    }

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


Work Items
----------

* Add a new RESTful API about copy
* Add copy API to karbor client

Dependencies
============



Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

None

References
==========
None
