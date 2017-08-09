.. -*- rst -*-

==============
Operation logs
==============

This API enables the Karbor user get the information about operation logs:

-  List all operation logs by a given project.
-  Show the information of a given operation log.

When you perform the above operation, these status values are possible:

+-----------------+----------------------------------------------------------+
| Status          | Description                                              |
+=================+==========================================================+
| available       | A protect operation is finished.                         |
+-----------------+----------------------------------------------------------+
| success         | A restore operation is success.                          |
+-----------------+----------------------------------------------------------+
| deleted         | A delete operation is finished.                          |
+-----------------+----------------------------------------------------------+


List operation logs
===================

.. rest_method:: GET /v1/{tenant_id}/operation_logs

List all operation logs, triggered by a given project, or part of the operation
logs limited by ``?limit={limit_num}`` by ``GET`` method.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: tenant_id
   - sort: sort
   - limit: limit
   - marker: marker

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - operation_logs: operation_log_list
   - id: operation_log_id
   - project_id: tenant_id_1
   - operation_type: operation_type
   - checkpoint_id: checkpoint_id_2
   - plan_id: plan_id_1
   - provider_id: provider_id_2
   - restore_id: restore_id_2
   - scheduled_operation_id: operation_id_2
   - status: operation_log_status
   - started_at: started_at
   - ended_at: ended_at
   - error_info: error_info
   - extra_info: extra_info
   - operation_logs_links: links

Response Example
----------------

.. literalinclude:: ./samples/operation-logs-list-response.json
   :language: javascript


Show operation log
==================

.. rest_method:: GET /v1/{tenant_id}/operation_logs/{operation_log_id}

Show the information of a given operation log.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: tenant_id
   - operation_log_id: operation_log_id_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - operation_log: operation_log
   - id: operation_log_id
   - project_id: tenant_id_1
   - operation_type: operation_type_1
   - checkpoint_id: checkpoint_id_2
   - plan_id: plan_id_1
   - provider_id: provider_id_2
   - restore_id: restore_id_2
   - scheduled_operation_id: operation_id_2
   - status: operation_log_status
   - started_at: started_at
   - ended_at: ended_at
   - error_info: error_info
   - extra_info: extra_info_1

Response Example
----------------

.. literalinclude:: ./samples/operation-log-show-response.json
   :language: javascript
