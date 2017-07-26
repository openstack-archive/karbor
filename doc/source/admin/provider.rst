=============================
Configure Protection Provider
=============================

Provider Configuration Files
----------------------------

Before starting the karbor-protection service, the admin needs to configure a
Protection Providers in /etc/karbor/providers.d/

Each file must contain the `provider` section with the following fields:

* name - name of the provider
* description - One sentence representing the provider
* id - unique id for the provider, should be generated with uuid4
* plugin - multiple plugin statements, for each protection plugin enabled.
  Available options are under the `karbor.protections` namespace entry point.
* bank - bank plugin used for this provider.
  Available options are under the `karbor.protections` namespace entry point.
* enabled - true or false, whether to load the provider or not

Each protection plugin and the bank require additional configuration. Each
plugin defines the section and configuration options.

The "OpenStack Infra Provider" is the default provider, and can be used,
removed, or serve as a base for other providers.

Example
~~~~~~~

.. code-block:: ini

    [provider]
    name = OS Infra Provider
    description = This provider uses OpenStack's own services (swift, cinder) as storage
    id = cf56bd3e-97a7-4078-b6d5-f36246333fd9
    plugin=karbor-volume-protection-plugin
    bank=karbor-swift-bank-plugin
    enabled = True

    [swift_client]
    swift_auth_url=http://10.229.47.230/identity/
    swift_user=admin
    swift_key=123456
    swift_tenant_name=admin

    [swift_bank_plugin]
    lease_expire_window=120
    lease_renew_window=100
    lease_validity_window=100

