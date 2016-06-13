============
Installation
============

Single-node Devstack Installation
=================================
In order to install Smaug using Devstack on a single node, add the following to
your local.conf, under [[local|localrc]]:

.. code-block:: none

        enable_plugin smaug http://git.openstack.org/openstack/smaug master
        enable_plugin smaug-dashboard http://git.openstack.org/openstack/smaug-dashboard master
        enable_service smaug-api
        enable_service smaug-operationengine
        enable_service smaug-protection
        # Smaug Dashboard depends on Horizon
        enable_service smaug-dashboard

Depenencies
===========

Heat
~~~~

.. code-block:: none

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

        enable_service n-cpu n-api n-crt n-cond n-sch n-novnc n-cauth


Neutron (optional)
~~~~~~~~~~~~~~~~~~

.. code-block:: none

        enable_service neutron q-svc q-agt q-dhcp q-meta
        disable_service n-net
