.. -*- rst -*-

====================
Scheduled operations
====================

This API enables the Karbor user to manage protection Operations:

-  Create a checkpoint for a given Protection Plan.
-  Delete unneeded checkpoints from the provider.
-  Status on a given Operation ID.

Scheduled operations are operations that will be executed when a specific
trigger is triggered.


List scheduled operations
=========================

.. rest_method:: GET /v1/{tenant_id}/scheduled_operations

List all the scheduled operations based on trigger and plan, or part of the
scheduled operations limited by ``?limit={limit_num}`` by ``GET`` method.

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
   - operations: operation_list
   - scheduled_operation: operation
   - id: operation_id
   - name: operation_name
   - description: description
   - operation_type: operation_type
   - trigger_id: trigger_id
   - operation_definition: operation_definition
   - enabled: enabled
   - plans_links: links

Response Example
----------------

.. literalinclude:: ./samples/scheduled-operations-list-response.json
   :language: javascript


Create scheduled operation
==========================

.. rest_method:: POST /v1/{tenant_id}/scheduled_operations

Create a new scheduled operation.

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
   - scheduled_operation: operation
   - name: operation_name
   - description: description
   - operation_type: operation_type
   - trigger_id: trigger_id
   - operation_definition: operation_definition

Request Example
---------------

.. literalinclude:: ./samples/scheduled-operation-create-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - scheduled_operation: operation
   - id: operation_id
   - name: operation_name
   - description: description
   - operation_type: operation_type
   - trigger_id: trigger_id
   - operation_definition: operation_definition
   - enabled: enabled

Response Example
----------------

.. literalinclude:: ./samples/scheduled-operation-create-response.json
   :language: javascript


Show scheduled operation
========================

.. rest_method:: GET /v1/{tenant_id}/scheduled_operations/{scheduled_operation_id}

Shows the specified scheduled operation information.

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
   - scheduled_operation_id: operation_id_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - scheduled_operation: operation
   - id: operation_id
   - name: operation_name
   - description: description
   - operation_type: operation_type
   - trigger_id: trigger_id
   - operation_definition: operation_definition
   - enabled: enabled

Response Example
----------------

.. literalinclude:: ./samples/scheduled-operation-create-response.json
   :language: javascript


Delete scheduled operation
==========================

.. rest_method::  DELETE /v1/{tenant_id}/scheduled_operations/{scheduled_operation_id}

Deletes a specific scheduled operation.

Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 202

Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: tenant_id
   - scheduled_operation_id: operation_id_1
