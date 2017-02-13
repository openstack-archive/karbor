.. -*- rst -*-

===========
Checkpoints
===========

This API enables the Karbor user to access and manage the checkpoints stored in
the protection provider:

-  List all checkpoints given a Bank ID.
-  Show Information on a given checkpoint ID.
-  Delete a checkpoint.
-  Create a checkpoint.

When you perform the above operation, these status values are possible:

+-----------------+----------------------------------------------------------+
| Status          | Description                                              |
+=================+==========================================================+
| error           | A checkpoint creation error occurred.                    |
+-----------------+----------------------------------------------------------+
| protecting      | The checkpoint is being created.                         |
+-----------------+----------------------------------------------------------+
| available       | The checkpoint is created, and available.                |
+-----------------+----------------------------------------------------------+
| deleting        | The checkpoint is being deleted.                         |
+-----------------+----------------------------------------------------------+
| deleted         | The checkpoint is deleted.                               |
+-----------------+----------------------------------------------------------+
| error-deleting  | A checkpoint deletion error occurred.                    |
+-----------------+----------------------------------------------------------+


List checkpoints
================

.. rest_method:: GET /v1/{tenant_id}/providers/{provider_id}/checkpoints

List all the checkpoints offered at the given provider, or part of checkpoints
limited by ``?limit={limit_num}`` by ``GET`` method.

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
   - provider_id: provider_id_1
   - sort: sort
   - limit: limit
   - marker: marker

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - checkpoints: checkpoint_list
   - id: checkpoint_id
   - project_id: tenant_id_1
   - status: checkpoint_status
   - protection_plan: plan
   - resource_graph: resource_graph
   - checkpoints_links: links

Response Example
----------------

.. literalinclude:: ./samples/checkpoints-list-response.json
   :language: javascript


Create checkpoint
=================

.. rest_method:: POST /v1/{tenant_id}/providers/{provider_id}/checkpoints

Execute the protect operation for the specified plan and create a checkpoint
at a given provider.

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
   - provider_id: provider_id_1
   - checkpoint: checkpoint
   - plan_id: plan_id
   - extra_info: extra_info

Request Example
---------------

.. literalinclude:: ./samples/checkpoint-create-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - checkpoint: checkpoint
   - id: checkpoint_id
   - project_id: tenant_id_1
   - status: checkpoint_status
   - protection_plan: plan
   - resource_graph: resource_graph

Response Example
----------------

.. literalinclude:: ./samples/checkpoint-create-response.json
   :language: javascript


Show checkpoint
===============

.. rest_method:: GET /v1/{tenant_id}/providers/{provider_id}/checkpoints/{checkpoint_id}

Shows the information about the specified checkpoint offered at a given
provider.

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
   - provider_id: provider_id_1
   - checkpoint_id: checkpoint_id_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - checkpoint: checkpoint
   - id: checkpoint_id
   - project_id: tenant_id_1
   - status: checkpoint_status
   - protection_plan: plan
   - resource_graph: resource_graph

Response Example
----------------

.. literalinclude:: ./samples/checkpoint-create-response.json
   :language: javascript


Delete checkpoint
=================

.. rest_method::  DELETE /v1/{tenant_id}/providers/{provider_id}/checkpoints/{checkpoint_id}

Deletes a specific checkpoint.

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
   - provider_id: provider_id_1
   - checkpoint_id: checkpoint_id_1

Response
--------

Empty dict

Response Example
----------------

.. literalinclude:: ./samples/checkpoint-delete-response.json
   :language: javascript
