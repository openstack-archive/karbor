.. _install-source:

Install from source
~~~~~~~~~~~~~~~~~~~


This section describes how to install and configure the Data Protection
service from source.

.. include:: common_prerequisites.rst

Install the services
--------------------

Retrieve and install karbor::

    git clone https://git.openstack.org/openstack/karbor
    cd karbor
    python setup.py install

This procedure installs the ``karbor`` python library and the following
executables:

* ``karbor-wsgi``: karbor wsgi script
* ``karbor-api``: karbor api script
* ``karbor-protection``: karbor protection script
* ``karbor-operationengine``: karbor operationengine script
* ``karbor-manage``: karbor manage script

Install sample configuration files::

    mkdir /etc/karbor
    cp etc/api-paste.ini /etc/karbor
    cp /etc/karbor.conf /etc/karbor
    cp /etc/policy.json /etc/karbor
    cp -r etc/providers.d /etc/karbor

Create the log directory::

    mkdir /var/log/karbor

.. note::

    Karbor provides more preconfigured providers with different bank and
    protection plugins (such as EISOO, S3, File system, Cinder snapshot
    plugin, and more). If these were available for your environment, you
    can consult these provider configuration files for reference, or use
    them as-is, by copying the configuration files from 'devstack/providers.d'
    to '/etc/karbor/providers.d'. By default, karbor use 'OS Infra Provider
    with swift bank'.

Install the client
------------------

Retrieve and install karbor client::

    git clone https://git.openstack.org/openstack/python-karborclient.git
    cd python-karborclient
    python setup.py install

.. include:: common_configure.rst

Finalize installation
---------------------

You can start karbor services directly from command line by executing
``karbor-api``, ``karbor-protection`` and ``karbor-operationengine``.
