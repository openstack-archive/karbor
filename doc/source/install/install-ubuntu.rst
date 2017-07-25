.. _install-ubuntu:

Install and configure for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Data Protection
service for Ubuntu 14.04 (LTS) and Ubuntu 16.04 (LTS).

.. include:: common_prerequisites.rst

Install and configure components
--------------------------------

#. Install the packages:

   .. code-block:: console

      # apt-get install karbor

.. include:: common_configure.rst

Finalize installation
---------------------

1. Restart the Data Protection services:

   .. code-block:: console

      # service karbor-api restart
      # service karbor-operationengine restart
      # service karbor-protection restart
