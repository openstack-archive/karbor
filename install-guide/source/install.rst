.. _install:

Install and configure
~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure Karbor, Application Data
Protection service, on the controller node.

This section assumes that you already have a working OpenStack
environment with at least the following components installed. These components are optional:
`Identity service (keystone) <https://docs.openstack.org/ocata/install-guide-ubuntu/keystone.html>`_.
and the following components may be installed:
`Compute service (nova) <https://docs.openstack.org/ocata/install-guide-ubuntu/nova.html>`_,
`Block Storage service (cinder) <https://docs.openstack.org/ocata/install-guide-ubuntu/cinder.html>`_,
`Image service (glance) <https://docs.openstack.org/ocata/install-guide-ubuntu/glance.html>`_.
and Default provider need the following components to be installed:
`Object Storage service (swift) <https://docs.openstack.org/project-install-guide/object-storage/ocata/>`_.

Note that installation and configuration vary by distribution.

.. toctree::
   :maxdepth: 1

   install-ubuntu.rst
