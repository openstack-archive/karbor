.. -*- rst -*-

========
Triggers
========

This API enables the Karbor user to access the trigger registry and do
the following operations:

-  Trigger CRUD.
-  List Triggers.


List triggers
=============

.. rest_method:: GET /v1/{tenant_id}/triggers

List all the triggers offered for the given project, or part of the triggers
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
   - sort: sort
   - limit: limit
   - marker: marker

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - triggers: trigger_list
   - id: trigger_id
   - type: trigger_type
   - name: trigger_name
   - properties: trigger_properties
   - plans_links: links

Response Example
----------------

.. literalinclude:: ./samples/triggers-list-response.json
   :language: javascript


Create trigger
==============

.. rest_method:: POST /v1/{tenant_id}/triggers

Create a new trigger.

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
   - trigger_info: trigger
   - type: trigger_type
   - name: trigger_name
   - properties: trigger_properties

Request Example
---------------

.. literalinclude:: ./samples/trigger-create-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - trigger_info: trigger
   - id: trigger_id
   - type: trigger_type
   - name: trigger_name
   - properties: trigger_properties

Response Example
----------------

.. literalinclude:: ./samples/trigger-create-response.json
   :language: javascript


Show trigger
============

.. rest_method:: GET /v1/{tenant_id}/triggers/{trigger_id}

Shows the information about a specified trigger.

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
   - trigger_id: trigger_id_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - trigger_info: trigger
   - id: trigger_id
   - type: trigger_type
   - name: trigger_name
   - properties: trigger_properties

Response Example
----------------

.. literalinclude:: ./samples/trigger-create-response.json
   :language: javascript


Update trigger
==============

.. rest_method:: PUT /v1/{tenant_id}/triggers/{trigger_id}

Updates the name or properties of a specific trigger alone or at the same
time.

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
   - trigger_id: trigger_id_1
   - trigger_info: trigger
   - name: trigger_name_1
   - properties: trigger_properties_1

Request Example
---------------

.. literalinclude:: ./samples/trigger-update-request.json
   :language: javascript

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - trigger_info: trigger
   - id: trigger_id
   - type: trigger_type
   - name: trigger_name
   - properties: trigger_properties

Response Example
----------------

.. literalinclude:: ./samples/trigger-update-response.json
   :language: javascript


Delete trigger
==============

.. rest_method::  DELETE /v1/{tenant_id}/triggers/{trigger_id}

Deletes a specific trigger.

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
   - trigger_id: trigger_id_1
