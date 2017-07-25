.. _install:

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure Karbor, Application Data
Protection service, on the controller node.

Before you begin, make sure you already have a working OpenStack environment.

Required components:

* `Identity service (keystone) <https://docs.openstack.org/keystone/latest/install>`_

Recommended components:

* `Compute service (nova) <https://docs.openstack.org/nova/latest/install>`_ 
* `Block Storage service (cinder) <https://docs.openstack.org/cinder/latest/install>`_
* `Image service (glance) <https://docs.openstack.org/glance/latest/install>`_
* `Object Storage service (swift) <https://docs.openstack.org/swift/latest/install>`_
* `Shared Filesystems service (manila) <https://docs.openstack.org/manila/latest/install>`_

Note that installation and configuration vary by distribution.

.. toctree::
   :maxdepth: 1

   install-source
   install-ubuntu
   mod_wsgi
