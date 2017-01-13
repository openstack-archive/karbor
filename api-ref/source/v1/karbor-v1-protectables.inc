.. -*- rst -*-

============
Protectables
============

Enables the Karbor user to access information about which resource types are
protectable (i.e. can be protected by Karbor).  In addition, enables the user
to get additional information on each resource type, such as a list of actual
instances and their dependencies.


List protectable types
======================

.. rest_method:: GET /v1/{tenant_id}/protectables

Lists all the available protectable types.

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
   - protectable_type: protectable_type

Response Example
----------------

.. literalinclude:: ./samples/protectables-list-response.json
   :language: javascript


Show protectable type
=====================

.. rest_method:: GET /v1/{tenant_id}/protectables/{protectable_type}

Shows the information of a given protectable type.

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
   - protectable_type: protectable_type_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - protectable_type: protectable_type_2
   - name: protectable_name
   - dependent_types: dependent_types

Response Example
----------------

.. literalinclude:: ./samples/protectable-show-response.json
   :language: javascript


List protectable instances
==========================

.. rest_method:: GET /v1/{tenant_id}/protectables/{protectable_type}/instances

List all the available instances for the given protectable type.

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
   - protectable_type: protectable_type_1

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - instances: protectable_instance_list
   - id: protectable_instance_id
   - type: protectable_type_3
   - name: protectable_instance_name
   - dependent_resources: dependent_resources
   - instances_links: links

Response Example
----------------

.. literalinclude:: ./samples/protectable-instances-list-response.json
   :language: javascript


Show protectable instance
=========================

.. rest_method::  GET /v1/{tenant_id}/protectables/{protectable_type}/instances/{resource_id}

Show the information about a specific instance and its immediate dependencies.

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
   - protectable_type: protectable_type_1
   - resource_id: resource_id

Response
--------

.. rest_parameters:: parameters.yaml

   - X-Openstack-Request-Id: request_id
   - instance: protectable_instance
   - id: protectable_instance_id
   - type: protectable_type_3
   - name: protectable_instance_name
   - dependent_resources: dependent_resources

Response Example
----------------

.. literalinclude:: ./samples/protectable-instance-show-response.json
   :language: javascript
