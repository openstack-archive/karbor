.. _install-ubuntu:

Install and configure for Ubuntu
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section describes how to install and configure the Data Protection
service for Ubuntu 14.04 (LTS) and Ubuntu 16.04 (LTS).

Prerequisites
-------------

Before you install and configure Data Protection service, you must create a
database, service credentials, and API endpoints. Data Protection service also
requires additional information in the Identity service.

#. To create the database, complete these steps:

   * Use the database access client to connect to the database
     server as the ``root`` user:

     .. code-block:: console

        $ mysql -u root -p

   * Create the ``karbor`` database:

     .. code-block:: console

        CREATE DATABASE karbor;

   * Grant proper access to the ``karbor`` database:

     .. code-block:: console

        GRANT ALL PRIVILEGES ON karbor.* TO 'karbor'@'localhost' IDENTIFIED BY 'KARBOR_DBPASS';
        GRANT ALL PRIVILEGES ON karbor.* TO 'karbor'@'%' IDENTIFIED BY 'KARBOR_DBPASS';

     Replace ``KARBOR_DBPASS`` with a suitable password.

   * Exit the database access client.

#. Source the ``admin`` credentials to gain access to
   admin-only CLI commands:

   .. code-block:: console

      $ . admin-openrc

#. To create the service credentials, complete these steps:

   * Create the ``karbor`` user:

     .. code-block:: console

        $ openstack user create --domain default --password-prompt karbor
        User Password:
        Repeat User Password:
        +-----------+----------------------------------+
        | Field     | Value                            |
        +-----------+----------------------------------+
        | domain_id | e0353a670a9e496da891347c589539e9 |
        | enabled   | True                             |
        | id        | ca2e175b851943349be29a328cc5e360 |
        | name      | karbor                           |
        +-----------+----------------------------------+

   * Add the ``admin`` role to the ``karbor`` user:

     .. code-block:: console

        $ openstack role add --project service --user karbor admin

     .. note::

        This command provides no output.

   * Create the ``karbor`` service entities:

     .. code-block:: console

        $ openstack service create --name karbor --description "Application Data Protection Service" data-protect
        +-------------+-------------------------------------+
        | Field       | Value                               |
        +-------------+-------------------------------------+
        | description | Application Data Protection Service |
        | enabled     | True                                |
        | id          | 727841c6f5df4773baa4e8a5ae7d72eb    |
        | name        | karbor                              |
        | type        | data-protect                        |
        +-------------+-------------------------------------+

#. Create the Data Protection service API endpoints:

   .. code-block:: console

      $ openstack endpoint create --region RegionOne data-protect public http://controller:8799/v1/%\(project_id\)s
      +--------------+------------------------------------------+
      | Field        | Value                                    |
      +--------------+------------------------------------------+
      | enabled      | True                                     |
      | id           | 3f4dab34624e4be7b000265f25049609         |
      | interface    | public                                   |
      | region       | RegionOne                                |
      | region_id    | RegionOne                                |
      | service_id   | 727841c6f5df4773baa4e8a5ae7d72eb         |
      | service_name | karbor                                   |
      | service_type | data-protect                             |
      | url          | http://controller:8799/v1/%(project_id)s |
      +--------------+------------------------------------------+

      $ openstack endpoint create --region RegionOne data-protect internal http://controller:8799/v1/%\(project_id\)s
      +--------------+------------------------------------------+
      | Field        | Value                                    |
      +--------------+------------------------------------------+
      | enabled      | True                                     |
      | id           | 3f4dab34624e4be7b000265f25049609         |
      | interface    | internal                                 |
      | region       | RegionOne                                |
      | region_id    | RegionOne                                |
      | service_id   | 727841c6f5df4773baa4e8a5ae7d72eb         |
      | service_name | karbor                                   |
      | service_type | data-protect                             |
      | url          | http://controller:8799/v1/%(project_id)s |
      +--------------+------------------------------------------+

      $ openstack endpoint create --region RegionOne data-protect admin http://controller:8799/v1/%\(project_id\)s
      +--------------+------------------------------------------+
      | Field        | Value                                    |
      +--------------+------------------------------------------+
      | enabled      | True                                     |
      | id           | 3f4dab34624e4be7b000265f25049609         |
      | interface    | admin                                    |
      | region       | RegionOne                                |
      | region_id    | RegionOne                                |
      | service_id   | 727841c6f5df4773baa4e8a5ae7d72eb         |
      | service_name | karbor                                   |
      | service_type | data-protect                             |
      | url          | http://controller:8799/v1/%(project_id)s |
      +--------------+------------------------------------------+

Install and configure components
--------------------------------

.. note::

   Default configuration files vary by distribution. You might need
   to add these sections and options rather than modifying existing
   sections and options. Also, an ellipsis (``...``) in the configuration
   snippets indicates potential default configuration options that you
   should retain.

#. Install the packages:

   .. code-block:: console

      # apt-get install karbor

2. Edit the ``/etc/karbor/karbor.conf`` file and complete the following
   actions:

   * In the ``[database]`` section, configure database access:

     .. code-block:: none

        [database]
        ...
        connection = mysql+pymysql://karbor:KARBOR_DBPASS@controller/karbor

     Replace ``KARBOR_DBPASS`` with the password you chose for the
     Data Protection database.

   * In the ``[DEFAULT]`` section,
     configure ``RabbitMQ`` message queue access:

     .. code-block:: none

        [DEFAULT]
        ...
        transport_url = rabbit://openstack:RABBIT_PASS@controller

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.

   * In the ``[keystone_authtoken]``, ``[trustee]``,
     ``[clients_keystone]``, and ``[karbor_client]`` sections,
     configure Identity service access:

     .. code-block:: none

        [keystone_authtoken]
        ...
        auth_uri = http://controller/identity
        auth_url = http://controller/identity_admin
        memcached_servers = controller:11211
        auth_type = password
        project_domain_name = default
        user_domain_name = default
        project_name = service
        username = karbor
        password = KARBOR_PASS

        [trustee]
        ...
        auth_type = password
        auth_url = http://controller/identity_admin
        username = karbor
        password = KARBOR_PASS
        user_domain_name = default

        [clients_keystone]
        ...
        auth_uri = http://controller/identity_admin

        [karbor_client]
        ...
        version = 1
        service_type = data-protect
        service_name = karbor

     Replace ``KARBOR_PASS`` with the password you chose for the
     ``karbor`` user in the Identity service.

3. Populate the Data Protection database:

   .. code-block:: console

      # su -s /bin/sh -c "karbor-manage db sync" karbor

   .. note::

      Ignore any deprecation messages in this output.

Finalize installation
---------------------

1. Restart the Data Protection services:

   .. code-block:: console

      # service karbor-api restart
      # service karbor-operationengine restart
      # service karbor-protection restart
