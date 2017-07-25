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
