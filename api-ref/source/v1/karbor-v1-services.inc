.. -*- rst -*-

========
Services
========
Administrator only. Lists all Karbor services, enables or disables a Karbor
service, freeze or thaw the specified karbor-operationengine host, failover a
replicating karbor-operationengine host.


List All Karbor Services
========================

.. rest_method:: GET /v1/{tenant_id}/os-services

Lists all Karbor services. Provides details why any services were disabled.


Response Codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403

Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: tenant_id
   - host: host_query
   - binary: binary_query

Response
--------

.. rest_parameters:: parameters.yaml

  - services: services
  - id: service_id
  - binary: binary_required
  - host: host_name_body_req
  - status: service_status
  - state: service_state_up_down
  - updated_at: updated
  - disabled_reason: disabled_reason_body_req

Response Example
----------------

.. literalinclude:: ./samples/services-list-response.json
   :language: javascript


Update a Karbor Service Status
==============================

.. rest_method:: PUT /v1/{tenant_id}/os-services/{service_id}

Update a Karbor operationengine service status. Specify the service by its id.

Response codes
--------------

.. rest_status_code:: success status.yaml

   - 200

.. rest_status_code:: error status.yaml

   - 400
   - 401
   - 403
   - 404

Request
-------

.. rest_parameters:: parameters.yaml

   - tenant_id: tenant_id
   - service_id: service_id_path

Request Example
---------------

.. literalinclude:: ./samples/services-update-request.json
   :language: javascript

Response Parameters
-------------------

.. rest_parameters:: parameters.yaml

  - service: service_body
  - id: service_id
  - binary: binary_required
  - host: host_name_body_req
  - status: service_status
  - state: service_state_up_down
  - updated_at: updated
  - disabled_reason: disabled_reason_body_req

Response Example
----------------

.. literalinclude:: ./samples/services-update-response.json
   :language: javascript
