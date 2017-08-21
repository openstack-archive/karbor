..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================================
Add checkpoint verification API about protection to Karbor
==========================================================

https://blueprints.launchpad.net/karbor/+spec/support-verify-the-checkpoint-api

Problem description
===================

User want to verify the backup copies in one checkpoint before he restoring new
resources from this checkpoint. If the verification about the backup copies in one
checkpoint fails, it means that the backup data is corrupted and invalid for recovering.
User can not restore the resource from this backup data of the checkpoint.
All backup softwares support verify the backup data copes[1] [2]. The verification
work can be done in the verification operation of the vendors protection plugins.

The verification operation for the plugin is optional, most of the plugins should
implement a verification operation.
For example, in the cinder backup volume plugin, the backup being still in place and
the status of backup can be checked in the verification operation of this plugin.
Some plugins can and should make sure metadata is accessible from the bank in the
verification operation of the plugins.


Use Cases
=========

User want to verify the backup copies in one checkpoint via a new RESTful API before
he restoring new resources form this checkpoint.
The backup softwares vendors also need karbor protection plugins to support a verification
operation, so that they can expose the verification of backup data to users from Karbor
protection service.


Proposed change
===============
1. Add the verification API controller for the Karbor API.
   Implement the 'create' method of verification API controller.
   Implement the 'show' method of verification API controller.
   Implement the 'index' method of verification API controller.

2. The status of verification resources.
   VERIFICATION_STATUS_VERIFYING = 'verifying'
   VERIFICATION_STATUS_SUCCESS = 'success'
   VERIFICATION_STATUS_ERROR = 'error'

3. Add a new verification operation for protection plugins

   Add a new VerificationOperation for protection plugins. The verification operation for
   the plugin is optional, most of the plugins should implement a verification operation.
   For example, the VerificationOperation of image protection plugin, the backup data in
   swift bank can be verified by checking the etag of objects in the swift.

   The VerificationOperation of cinder protection plugin, default cinder volume plugin don't
   support volume backup data verification, cinder has not expose the api about backup
   data verification. So we can check the backup being still in place and the status of
   backup resources in Cinder.
   Some plugins can and should make sure metadata is accessible from the bank in the
   verification operation of the plugins.


4. Add operation_log for verification API.
   Add a new verification flow in the protection service of Karbor.
   If the VerificationOperation about the checkpoint has not run successfully in the
   verification flow, the status of operation_log object will be set to 'error' in the
   'revert' method of InitiateVerificationTask. The status of operation_log object will
   be set to 'success' in the CompleteVerificationTask.


Alternatives
------------

None

Data model impact
-----------------

+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | varchar(36)  | NO   | PRI | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| project_id              | varchar(255) | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| provider_id             | varchar(36)  | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| checkpoint_id           | varchar(36)  | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| status                  | varchar(64)  | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| parameters              | Text         | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| resources_status        | Text         | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| resources_reason        | Text         | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| created_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| updated_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+
| deleted_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+

REST API impact
---------------

1. Create verification  API
The request JSON when creating a verification::

    **post** : /v1/{project_id}/verifications
    ```json
    {
      "verification": [
        {
          "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
          "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
          "parameters": {
            "OS::Cinder::Volume": {
            },
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
            }
          }
        }
      ]
    }


The response JSON when Creating a verification::

    ```json
    {
        "verification":{
          "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
          "project_id": "e486a2f49695423ca9c47e589b948108",
          "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
          "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
          "parameters": {
            "OS::Cinder::Volume": {
            },
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
            }
          },
          "resource_status": {
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": "verifying",
            "OS::Cinder::Volume#98eb847f-9f59-4d54-8b7b-5047bd2fa4c7": "error"
          },
          "resource_reason": {
            "OS::Cinder::Volume#98eb847f-9f59-4d54-8b7b-5047bd2fa4c7": "Backup not found"
          },
          "status": "error"
        }
    }



2. List verifications  API
The response JSON when listing verifications::

    **get** : /v1/{project_id}/verifications
    ```json
    {
      "verifications": [
        {
          "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
          "project_id": "e486a2f49695423ca9c47e589b948108",
          "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
          "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
          "parameters": {
            "OS::Cinder::Volume": {
            },
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
            }
          },
          "resource_status": {
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": "verifying",
            "OS::Cinder::Volume#98eb847f-9f59-4d54-8b7b-5047bd2fa4c7": "error"
          },
          "resource_reason": {
            "OS::Cinder::Volume#98eb847f-9f59-4d54-8b7b-5047bd2fa4c7": "Backup not found"
          },
          "status": "error"
        }
      ]
    }


3. Show verifications API
The response JSON when showing a verification::

    **get** : /v1/{project_id}/verifications/{verification_id}
    ```json
    {
        "verification":{
          "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
          "project_id": "e486a2f49695423ca9c47e589b948108",
          "provider_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
          "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
          "parameters": {
            "OS::Cinder::Volume": {
            },
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": {
            }
          },
          "resource_status": {
            "OS::Nova::Server#3f8af6c6-ecea-42bd-b44c-724785bbe5ea": "verifying",
            "OS::Cinder::Volume#98eb847f-9f59-4d54-8b7b-5047bd2fa4c7": "error"
          },
          "resource_reason": {
            "OS::Cinder::Volume#98eb847f-9f59-4d54-8b7b-5047bd2fa4c7": "Backup not found"
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

* Add a new RESTful API about verification
* Add database data module of verification
* Add verification to karbor client

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

[1] http://documentation.commvault.com/commvault/v10/article?p=features/data_verification/data_verification.htm

[2] https://www.veritas.com/content/support/en_US/doc-viewer.123533878-127136857-0.v123545982-127136857.html

