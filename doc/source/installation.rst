============
Installation
============

Single-node Devstack Installation
=================================
In order to install Karbor using Devstack on a single node, add the following to
your local.conf, under [[local|localrc]]:

.. code-block:: none

        enable_plugin karbor https://git.openstack.org/openstack/karbor master
        enable_plugin karbor-dashboard https://git.openstack.org/openstack/karbor-dashboard master
        enable_service karbor-api
        enable_service karbor-operationengine
        enable_service karbor-protection
        # Karbor Dashboard depends on Horizon
        enable_service karbor-dashboard

Dependencies
============

Heat
~~~~

.. code-block:: none

        enable_plugin heat https://git.openstack.org/openstack/heat master
        enable_service h-eng h-api h-api-cfn h-api-cw

Swift (recommended)
~~~~~~~~~~~~~~~~~~~

Essential for the basic protection provider.

.. code-block:: none

        SWIFT_REPLICAS=1
        SWIFT_HASH=66a3d6b56c1f479c8b4e70ab5c2000f5
        SWIFT_DATA_DIR=$DEST/data
        enable_service s-proxy s-object s-container s-account

Cinder (optional)
~~~~~~~~~~~~~~~~~

.. code-block:: none

        enable_service cinder c-api c-vol c-sch c-bak

Glance (optional)
~~~~~~~~~~~~~~~~~

.. code-block:: none

        enable_service g-api g-reg

Nova (optional)
~~~~~~~~~~~~~~~

.. code-block:: none

        enable_service n-cpu n-api n-cond n-sch n-novnc n-cauth placement-api


Neutron (optional)
~~~~~~~~~~~~~~~~~~

.. code-block:: none

        enable_service neutron q-svc q-agt q-dhcp q-meta
        disable_service n-net
