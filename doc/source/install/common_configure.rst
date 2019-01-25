#. Edit the ``/etc/karbor/karbor.conf`` file and complete the following
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
        transport_url = rabbit://openstack:RABBIT_PASS@controller:5672

     Replace ``RABBIT_PASS`` with the password you chose for the
     ``openstack`` account in ``RabbitMQ``.

   * In the ``[keystone_authtoken]``, ``[trustee]``,
     ``[clients_keystone]``, and ``[karbor_client]`` sections,
     configure Identity service access:

     .. code-block:: none

        [keystone_authtoken]
        ...
        www_authenticate_uri = http://keystone1.example.com/identity
        auth_url = http://controller/identity_admin
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

#. Populate the Data Protection database:

   .. code-block:: console

      # su -s /bin/sh -c "karbor-manage db sync" karbor

   .. note::

      Ignore any deprecation messages in this output.
