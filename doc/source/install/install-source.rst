.. _install-source:

Install from source
~~~~~~~~~~~~~~~~~~~


This section describes how to install and configure the Data Protection
service from source.

.. include:: common_prerequisites.rst

Install the services
--------------------

Retrieve and install karbor with required packages::

    git clone https://git.openstack.org/openstack/karbor
    cd karbor
    sudo pip install -e .
    python setup.py install

This procedure installs the ``karbor`` python library and the following
executables:

* ``karbor-wsgi``: karbor wsgi script
* ``karbor-api``: karbor api script
* ``karbor-protection``: karbor protection script
* ``karbor-operationengine``: karbor operationengine script
* ``karbor-manage``: karbor manage script

Generate sample configuration file karbor.conf.sample::

    #use tox
    tox -egenconfig
    #or direct run oslo-config-generator
    oslo-config-generator --config-file etc/oslo-config-generator/karbor.conf

Generate sample policy file policy.yaml.sample::

    #use tox
    tox -egenpolicy
    #or direct run oslopolicy-sample-generator
    oslopolicy-sample-generator --config-file=etc/karbor-policy-generator.conf

Install sample configuration files::

    mkdir /etc/karbor
    cp etc/api-paste.ini /etc/karbor
    cp etc/karbor.conf.sample /etc/karbor/karbor.conf
    cp etc/policy.yaml.sample /etc/karbor/policy.yaml
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

Configure components
--------------------

#. Add system user::

    groupadd karbor
    useradd karbor -g karbor -d /var/lib/karbor -s /sbin/nologin

.. include:: common_configure.rst

Finalize installation
---------------------

You can start karbor services directly from command line by executing
``karbor-api``, ``karbor-protection`` and ``karbor-operationengine``.
