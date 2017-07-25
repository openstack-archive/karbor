.. _verify:

Verify operation
~~~~~~~~~~~~~~~~

Verify operation of the Data Protection service.

.. note::

   Perform these commands on the controller node.

#. Source the ``admin`` tenant credentials:

   .. code-block:: console

      $ . admin-openrc

#. List and show service components to verify successful launch and
   registration of each process:

   .. code-block:: console

      $ openstack service list |grep data-protect
      | dedab9a746e34d3990ca44bc2e885b49 | karbor      | data-protect   |

      $ openstack service show dedab9a746e34d3990ca44bc2e885b49
      +-------------+-------------------------------------+
      | Field       | Value                               |
      +-------------+-------------------------------------+
      | description | Application Data Protection Service |
      | enabled     | True                                |
      | id          | dedab9a746e34d3990ca44bc2e885b49    |
      | name        | karbor                              |
      | type        | data-protect                        |
      +-------------+-------------------------------------+
