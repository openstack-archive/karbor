.. -*- rst -*-

========
Restores
========

This API enables the Karbor user restore a checkpoint on to a restore target:

-  List all restores by a given project.
-  Create restored system from a checkpoint.
-  Show the information of a given restore operation.

When you perform the above operation, these status values are possible:

+-----------------+----------------------------------------------------------+
| Status          | Description                                              |
+=================+==========================================================+
| started         | A restore operation is in progress.                      |
+-----------------+----------------------------------------------------------+
| success         | A restore operation is success.                          |
+-----------------+----------------------------------------------------------+
| failed          | A restore operation is failed.                           |
+-----------------+----------------------------------------------------------+


List restores
=============

.. rest_method:: GET /v1/{tenant_id}/restores

List all restores started, success or failed, triggered by a given project,
or part of the protection plans limited by ``?limit={limit_num}`` by ``GET``
method.

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
   - restores: restore_list
   - id: restore_id
   - project_id: tenant_id_1
   - provider_id: provider_id
   - checkpoint_id: checkpoint_id
   - restore_target: restore_target
   - parameters: restore_parameters
   - status: restore_status
   - resource_status: restore_resource_status
   - resource_reason: restore_resource_reason
   - restores_links: links

Response Example
----------------

.. literalinclude:: ./samples/restores-list-response.json
   :language: javascript


Create restore
==============

.. rest_method:: POST /v1/{tenant_id}/restores

Start a restore operation.

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
   - restore: restore
   - provider_id: provider_id
   - checkpoint_id: checkpoint_id
   - restore_target: restore_target
   - restore_auth: restore_auth
   - parameters: restore_parameters

Request Example
---------------

.. literalinclude:: ./samples/restore-create-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - restore: restore
   - id: restore_id
   - project_id: tenant_id_1
   - provider_id: provider_id
   - checkpoint_id: checkpoint_id
   - restore_target: restore_target
   - restore_auth: restore_auth
   - parameters: restore_parameters
   - status: restore_status
   - resource_status: restore_resource_status
   - resource_reason: restore_resource_reason

Response Example
----------------

.. literalinclude:: ./samples/restore-create-response.json
   :language: javascript


Show restore
============

.. rest_method:: GET /v1/{tenant_id}/restores/{restore_id}

Show the information of a given restore operation.

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
   - restore_id: restore_id_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - restore: restore
   - id: restore_id
   - project_id: tenant_id_1
   - provider_id: provider_id
   - checkpoint_id: checkpoint_id
   - restore_target: restore_target
   - parameters: restore_parameters
   - status: restore_status
   - resource_status: restore_resource_status
   - resource_reason: restore_resource_reason

Response Example
----------------

.. literalinclude:: ./samples/restore-create-response.json
   :language: javascript
