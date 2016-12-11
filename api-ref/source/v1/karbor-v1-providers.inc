.. -*- rst -*-

=========
Providers
=========

Enables the Karbor user to list available providers and get parameters and
result schema super-set for all plugins of a specific Provider.


List protection providers
=========================

.. rest_method:: GET /v1/{tenant_id}/providers

List all the information about the providers offered at a given service, or
part of the providers limited by ``?limit={limit_num}`` by ``GET`` method.
All providers need to be configured first by the admin.

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
   - providers: provider_list
   - id: provider_id
   - name: provider_name
   - description: description
   - extended_info_schema: schema_extended_info
   - saved_info_schema: schema_saved_info
   - restore_schema: schema_restore
   - providers_links: links

Response Example
----------------

.. literalinclude:: ./samples/providers-list-response.json
   :language: javascript


Show protection provider
========================

.. rest_method:: GET /v1/{tenant_id}/providers/{provider_id}

Shows the information about a specific provider.

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

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - provider: provider
   - id: provider_id
   - name: provider_name
   - description: description
   - extended_info_schema: schema_extended_info
   - saved_info_schema: schema_saved_info
   - restore_schema: schema_restore

Response Example
----------------

.. literalinclude:: ./samples/provider-show-response.json
   :language: javascript
