..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

================================================
Add operation log API about protection to Karbor
================================================

https://blueprints.launchpad.net/karbor/+spec/operation-log-api

Problem description
===================

#usecase 1
The resources in a plan can be protected automatically or manually by the end user
via the checkpoint POST API. And then the checkpoints (about the metadata and backup
data) are created.

The checkpoints also can be deleted manually by end user via checkpoint DELETE API.
In the bp **Checkpoint scheduled clean**, the parameters max_backups and
retention_duration will be introduced to karbor. So the checkpoints also can be
deleted automatically.

But if the end user want to query deleted protection log in history, he can not get
these deleted protection log via checkpoint restful API.

#usecase 2
Now user also want to query the logs about the operations like restore, delete, etc via
one RESTful API..

Use Cases
=========

User want to query all the operation logs via a uniform RESTful API, including all
the logs for different operation type(protect/restore/delete).

So the operation logs not only include logs for checkpoint, also include the logs for
restore and delete operation.

Proposed change
===============

As we know, the Checkpoint is responsible for the model of backup data which records
all the metadata of backup data in the whole lifecycle, it is not responsible for the
model of protection log. So Karbor need expose one RESTful api to support that the
end-user can query all the protection log about the plan including available, error
and deleted log records.
About this patch: Add operation log endpoints to API document[1]. We have a plan to
add operation log API to Karbor. But in this patch, we only consider the situation
that the checkpoints are created automatically via scheduled_operation API. We also
need consider the situation that the checkpoints are created manually directly via
checkpoint API. We need redesign the operation log API to meet above requirement.

We also need consider that operation logs about restore and delete, so we add a filed
operation_type to data module. Its value could be protect, delete, restore.

The "extra_info" field of operation log data module can be used for saving the detail
information by the vendor's plugin. For example: the job/task id and job/task description
about this protect operation action from the plugin backend, the backup software can be saved
to this field. So the tenant and admin can query this detail information about this
operation from the backup software via the operation log API.


1. The status of operation log::
OPERATION_LOGS_PROTECTING = 'protecting'
OPERATION_LOGS_AVAILABLE = 'available'
OPERATION_LOGS_STATUS_ERROR = 'error'
OPERATION_LOGS_DELETING = 'deleting'
OPERATION_LOGS_DELETED = 'deleted'
OPERATION_LOGS_DELETING = 'restoring'
OPERATION_LOGS_DELETED = 'restored'
OPERATION_LOGS_ERROR_DELETING = 'error-deleting'
OPERATION_LOGS_ERROR_DELETING = 'error-restoring'

2. Create
The checkpoint can be created manually directly via checkpoint API. In this situation,
The scheduled_operation_id filed of operation_log versioned object is None.
When the checkpoint is created automatically via scheduled_operation API. The value of
scheduled_operation_id can be get from the 'extra-info' of checkpoint POST API. This value
can be set to the filed of operation_log versioned object.
The operation_log object will be created after the checkpoint object being created in
RPC method 'protect' of protect service manager.

When a checkpoint is deleted manually directly via checkpoint API. In this situation, a
operation_log object about delete operation type need be created.

When a checkpoint is restored manually directly via checkpoint API. In this situation, a
operation_log object about restore operation type need be created.


2. Update the status of operation_log.
If the checkpoint has not created successfully in the protect flow. The status of operation_log
object will be set to 'error' in the 'revert' method of InitiateProtectTask.
The status of operation_log object will be set to 'available' in the CompleteProtectTask,
the end_time of object also will be updated.

When the user want to delete a checkpoint, the status of operation_log object will be set to
'deleted' after the checkpoint being deleted.

When the user want to restore a checkpoint, the status of operation_log object will be set to
'restored' after the checkpoint being restored.

Alternatives
------------

None

Data model impact
-----------------

+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | varchar(36)  | NO   | PRI | NULL    |       |
| project_id              | varchar(255) | NO   |     | NULL    |       |
| operation_type          | varchar(255) | NO   |     | NULL    |       |
| checkpoint_id           | varchar(36)  | YES  |     | NULL    |       |
| plan_id                 | varchar(36)  | YES  |     | NULL    |       |
| provider_id             | varchar(36)  | YES  |     | NULL    |       |
| restore_id              | varchar(36)) | YES  |     | NULL    |       |
| scheduled_operation_id  | varchar(36)) | YES  |     | NULL    |       |
| status                  | varchar(64)  | YES  |     | NULL    |       |
| started_at              | Datetime     | YES  |     | NULL    |       |
| ended_at                | Datetime     | YES  |     | NULL    |       |
| error_info              | Text         | YES  |     | NULL    |       |
| extra_info              | Text         | YES  |     | NULL    |       |
| created_at              | Datetime     | YES  |     | NULL    |       |
| updated_at              | Datetime     | YES  |     | NULL    |       |
| deleted_at              | Datetime     | YES  |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+

REST API impact
---------------

1. List operation_logs  API
The response JSON when listing operation logs::

    **get** : /v1/{project_id}/providers/{provider_id}/operation_logs
    ```json
    {
        "operation_logs":[
            {
                "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
                "project_id": "e486a2f49695423ca9c47e589b948108",
                "operation_type": "protect",
                "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
                "plan_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
                "provider_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
                "restore_id": None,
                "scheduled_operation_id": "23902b02-5666-4ee6-8dfe-962ac09c3991",
                "started_at": "2015-08-27T09:50:58-05:00",
                "ended_at": "2015-08-27T10:50:58-05:00",
                "status": "protecting",
                "error_info": "Could not access bank"
                "extra_info": {
                    "tsm_job_id": 10,
                    "rate": 20
                }
            }
        ]
    }


2. Show operation_logs API
The response JSON when showing a operation log::

    **get** : /v1/{project_id}/providers/{provider_id}/operation_logs/{operation_log_id}
    ```json
    {
        "operation_log":{
            "id": "22b82aa7-9179-4c71-bba2-caf5c0e68db7",
            "project_id": "e486a2f49695423ca9c47e589b948108",
            "operation_type": "protect",
            "checkpoint_id": "dcb20606-ad71-40a3-80e4-ef0fafdad0c3",
            "plan_id": "cf56bd3e-97a7-4078-b6d5-f36246333fd9",
            "provider_id": "23902b02-5666-4ee6-8dfe-962ac09c3994",
            "restore_id": None,
            "scheduled_operation_id": "23902b02-5666-4ee6-8dfe-962ac09c3991",
            "started_at": "2015-08-27T09:50:58-05:00",
            "ended_at": "2015-08-27T10:50:58-05:00",
            "status": "protecting",
            "error_info": "Could not access bank"
            "extra_info": {
                "tsm_job_id": 10,
                "rate": 20
            }
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

* Add a new RESTful API about operation log
* Add database data module of operation log
* Add operation log to karbor client

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

[1]  https://review.openstack.org/#/c/298060/

