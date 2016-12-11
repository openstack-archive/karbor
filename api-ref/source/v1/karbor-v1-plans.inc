.. -*- rst -*-

=====
Plans
=====

This API enables the Karbor user to access the protection Plan registry and do
the following operations:

-  Plan CRUD.
-  List Plans.
-  Starting and suspending of plans.

When you perform the above operation, these status values are possible:

+-----------------+----------------------------------------------------------+
| Status          | Description                                              |
+=================+==========================================================+
| started         | A plan is updated.                                       |
+-----------------+----------------------------------------------------------+
| suspended       | A plan is created.                                       |
+-----------------+----------------------------------------------------------+


List plans
==========

.. rest_method:: GET /v1/{tenant_id}/plans

List all the protection plans offered for the given project, or part of the
protection plans limited by ``?limit={limit_num}`` by ``GET`` method.

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
   - plans: plan_list
   - id: plan_id
   - name: plan_name
   - resources: resources
   - status: plan_status
   - provider_id: provider_id
   - parameters: plan_parameters
   - plans_links: links

Response Example
----------------

.. literalinclude:: ./samples/plans-list-response.json
   :language: javascript


Create plan
===========

.. rest_method:: POST /v1/{tenant_id}/plans

Create a new plan.

To specify the parameters for this plan, include the parameters
in the ``parameters`` attribute in the request body.

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
   - plan: plan
   - name: plan_name
   - resources: resources
   - provider_id: provider_id
   - parameters: plan_parameters

Request Example
---------------

.. literalinclude:: ./samples/plan-create-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - plan: plan
   - id: plan_id
   - name: plan_name
   - resources: resources
   - status: plan_status
   - provider_id: provider_id
   - parameters: plan_parameters

Response Example
----------------

.. literalinclude:: ./samples/plan-create-response.json
   :language: javascript


Show plan
=========

.. rest_method:: GET /v1/{tenant_id}/plans/{plan_id}

Shows the information about a specific plan.

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
   - plan_id: plan_id

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - plan: plan
   - id: plan_id
   - name: plan_name
   - resources: resources
   - status: plan_status
   - provider_id: provider_id
   - parameters: plan_parameters

Response Example
----------------

.. literalinclude:: ./samples/plan-create-response.json
   :language: javascript


Update plan
===========

.. rest_method:: PUT /v1/{tenant_id}/plans/{plan_id}

Updates a specific plan.

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
   - plan_id: plan_id
   - plan: plan
   - name: plan_name_1
   - resources: resources_1
   - status: plan_status_1

Request Example
---------------

.. literalinclude:: ./samples/plan-update-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - plan: plan
   - id: plan_id
   - name: plan_name
   - resources: resources
   - status: plan_status
   - provider_id: provider_id
   - parameters: plan_parameters

Response Example
----------------

.. literalinclude:: ./samples/plan-update-response.json
   :language: javascript


Delete plan
===========

.. rest_method::  DELETE /v1/{tenant_id}/plans/{plan_id}

Deletes a specific plan.

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
   - plan_id: plan_id
