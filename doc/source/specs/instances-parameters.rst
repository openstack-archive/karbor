..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Add parameters field for protectable instances API
===================================================

https://blueprints.launchpad.net/cinder/+spec/custom-checkpoint-metadata

Problem description
===================

Now the resource instances only can be queried from default region. If there are
several regions in one site/keystone, we can not query resource instances
from different region endpoint. We may need a parameter for the region name.

The scene of database protection: If we want to use Protectable Instances API to
query database instances from vendor's backup software. We must pass some parameters
about authentication to the RESTfull API of vendor's backup software.

I think we should add a dict type parameter to Protectable Instances API. The key
and value in parameter, which is needed for implementing some Protectable plugins.


Use Cases
=========

Scenario #1
User need a parameter for the region name to query resource instances from different
region endpoint.

Scenario #2
User uses the Protectable Instances API to query database instances from the vendor's
backup software. User must provide some parameters about authentication to the RESTfull
API of the vendor's backup software.

A dict type parameter is needed for Protectable Instances API. And it is optional.

Proposed change
===============

Add a new field parameters to the params of request for Protectable Instances API.

  /{project_id}/protectables/{protectable_type}/instances:
    get:
      summary: Resource Instances
      description: |
        Return all the available instances for the given protectable type.
      parameters:
        - $ref: '#/parameters/projectParam'
        - $ref: '#/parameters/protectable_typeParam'
        - $ref: '#/parameters/nameFilterParam'
        - $ref: '#/parameters/sortParam'
        - $ref: '#/parameters/limitParam'
        - $ref: '#/parameters/markerParam'
        - $ref: '#/parameters/ParametersParam'

The params of request: A dictionary-like object containing both the parameters from
the query string and request body.

Convert the data of parameters to the query string of API.

For example:

"parameters": {
    "region_name": "USA"
}

Add the query string about the parameters to Protectable Instances API.


/{project_id}/protectables/{protectable_type}/instances?parameters=%7B%27region_name%27%3A+%27USA%27%7D




Alternatives
------------

Do nothing, this is not a mission critical feature.

Data model impact
-----------------

None

REST API impact
---------------

Add a new field parameters to the params of request for Protectable Instances API.::

  /{project_id}/protectables/{protectable_type}/instances:
    get:
      summary: Resource Instances
      description: |
        Return all the available instances for the given protectable type.
      parameters:
        - $ref: '#/parameters/projectParam'
        - $ref: '#/parameters/protectable_typeParam'
        - $ref: '#/parameters/nameFilterParam'
        - $ref: '#/parameters/sortParam'
        - $ref: '#/parameters/limitParam'
        - $ref: '#/parameters/markerParam'
        - $ref: '#/parameters/ParametersParam'

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The new API will be exposed to users via the python-karborclient.

Performance Impact
------------------

None

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* Write API
* Add to Karbor client
* Write tests
* Add a usage example for API

Dependencies
============

None


Testing
=======

Unit tests in Karbor and the python-karborclient.


Documentation Impact
====================

Add a usage example for API.


References
==========

None
