.. -*- rst -*-

=============
Verifications
=============

This API enables the Karbor user to do verifications of the specify checkpoint:

-  Create a verification for a given checkpoint.
-  List all verifications of a given project.
-  Show the information of a given verification.

When you perform the above operation, these status values are possible:

+-----------------+----------------------------------------------------------+
| Status          | Description                                              |
+=================+==========================================================+
| in_progress     | A verify operation is in progress.                       |
+-----------------+----------------------------------------------------------+
| success         | A verify operation is success.                           |
+-----------------+----------------------------------------------------------+
| fail            | A verify operation is failed.                            |
+-----------------+----------------------------------------------------------+


List All Verifications
======================

.. rest_method:: GET /v1/{tenant_id}/verifications

Lists all verifications offered for the given project.


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

  - verifications: verifications
  - id: verification_id
  - project_id: tenant_id_1
  - provider_id: provider_id
  - checkpoint_id: checkpoint_id
  - parameters: verification_parameters
  - status: verification_status
  - resources_status: resources_status
  - resources_reason: resources_reason
  - verifications_links: verifications_links

 Response Example
----------------

.. literalinclude:: ./samples/verifications-list-response.json
   :language: javascript


Create verification
===================

.. rest_method:: PUT /v1/{tenant_id}/verifications

Execute the verify operation for the specified provider and checkpoint.

Response codes
--------------

.. rest_status_code:: success ../status.yaml

   - 200

.. rest_status_code:: error ../status.yaml

   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

   - verification: verification
   - provider_id: provider_id
   - checkpoint_id: checkpoint_id
   - parameters: verification_parameters

Request Example
---------------

.. literalinclude:: ./samples/verification-create-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - verification: verification
  - id: verification_id
  - project_id: tenant_id_1
  - provider_id: provider_id
  - checkpoint_id: checkpoint_id
  - parameters: verification_parameters
  - status: verification_status
  - resources_status: resources_status
  - resources_reason: resources_reason

Response Example
----------------

.. literalinclude:: ./samples/verification-create-response.json
   :language: javascript


Show Verification
=================

.. rest_method:: GET /v1/{tenant_id}/verifications/{verification_id}

Show the information of a given verify operation.


Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 401
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: tenant_id
   - verification_id: verification_id_path

Response
--------

.. rest_parameters:: parameters.yaml

  - verification: verification
  - id: verification_id
  - project_id: tenant_id_1
  - provider_id: provider_id
  - checkpoint_id: checkpoint_id
  - parameters: verification_parameters
  - status: verification_status
  - resources_status: resources_status
  - resources_reason: resources_reason

 Response Example
----------------

.. literalinclude:: ./samples/verification-create-response.json
   :language: javascript

