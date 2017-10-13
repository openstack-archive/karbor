..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Add service management API to Karbor
====================================

https://blueprints.launchpad.net/karbor/+spec/karbor-service-management

Problem description
===================

Currently, karbor does not have service management API for karbor services
(karbor-operationengine and karbor-protection). We can find that service
management API has been in almost all the other OpenStack projects. It is very
convenient for admin to list/enable/disable the services on any nodes.

Use Cases
=========

Admin want to list/enable/disable karbor services on any karbor nodes.

Proposed change
===============
1. Add service management API controller for the Karbor API.

  Implement the 'index' method of service management API controller.
  Implement the 'update' method of service management API controller.

2. Add service management to karbor client.

Alternatives
------------

None

Data model impact
-----------------

None

REST API impact
---------------

1. List services API
The response JSON when listing services::

    **get** : /v1/{project_id}/os-services
    ```json
    {
      "services": [
        {
          "status": "enabled",
          "binary": "karbor-operationengine",
          "disabled_reason": null,
          "host": "karbor@node",
          "updated_at": "2017-09-07T13:03:57.000000",
          "state": "up",
          "id": 1
        },
        {
          "status": "enabled",
          "binary": "karbor-protection",
          "disabled_reason": null,
          "host": "karbor@node",
          "updated_at": "2017-09-07T13:03:57.000000",
          "state": "up",
          "id": 2
        }
      ]
    }


2. Update service API
The request JSON when updating service::

    **put** : /v1/{project_id}/os-services/{service_id}
    ```json
    {
      "status": "enable"
    }


The response JSON when updating service::

    ```json
    {
      "service": {
        "id": "e81d66a4-ddd3-4aba-8a84-171d1cb4d339",
        "binary": "karbor-protection",
        "disabled_reason": null,
        "host": "karbor@node",
        "state": "up",
        "status": "enabled",
        "updated_at": "2012-10-29T13:42:05.000000",
      }
    }


Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

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

Primary assignee:
Jiao Pengju <jiaopengju@cmss.chinamobile.com>

Work Items
----------

* Add a new RESTful API about service management
* Add service management to karbor client

Dependencies
============

None

Testing
=======

Unit tests in Karbor.

Documentation Impact
====================

None

References
==========

None
