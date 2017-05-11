..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

============================================
Refactor the clients used in protect service
============================================

https://blueprints.launchpad.net/karbor/+spec/refactor-clients

Problem description
===================

As the bug[1] said, the user token may expire during the process of protection
when using it directly to access other openstack services.

Use Cases
=========

In protection service, both protect and restore operations use user token passed
by context to create clients of other openstack services and access them by that
client. It may fail to access other services because of the expiration of user
token.

Proposed change
===============

Recently, Keystone has merged a new spec[2] that resolves the issue of token
expiration which happens in access between multiple openstack services. Simply,
the principle is like this. When the Keystone Middleware validates the user
token, it will check the service token first. If it is passed and valid, then
Keystone allows user token to be fetched even if it is expired unless the time
exceeds the max window time which is set in Keystone and the default value is
48 hours.

It fixes Karbor's issue perfectly. According to that spec, Karbor can access
other openstack services successfully for 48 hours which is enough to finish all
the protect/restore works. There are some changes to create and use the clients
of other services before using that new mechanism.

1. create client
    The client may be created like this.

    def create(context):
        # user_auth_plugin: created by context, which stores the user token.
        # service_auth_pluing: created and initialized by service information of
        #                      Karbor which are registered to Keystone
        auth_plugin = service_token.ServiceTokenAuthWrapper(
            user_auth_plugin, service_auth_plugin)

        session = session.Session(auth=auth_plugin, verify=verify)

        # endpoint: the public url of cinder
        client = cinderclient.Client('3', session=session,
                                     endpoint_override=endpoint)

2. use client
    The client can be created once and used all the time until the max expiration
    time(48h).

Alternatives
------------

The 'trust' mechanism of Keystone can solve this issue. But it is a bit more
complex than the new one.

Data model impact
-----------------

None

REST API impact
---------------

None

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

It may spend some time to apply a new service token from Keystone
if it is expired when using the client to send the request each time.

Other deployer impact
---------------------

None

Developer impact
----------------

The developers of protect plugins should know these changes.


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* refactor all clients of other openstack services been using
in protect service.

Dependencies
============

It depends on all the patches[3] of Keystone to be merged.

Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

None

References
==========

[1] https://bugs.launchpad.net/karbor/+bug/1566793
[2] http://specs.openstack.org/openstack/keystone-specs/specs/keystone/ocata/allow-expired.html
[3] https://review.openstack.org/#q,topic:bp/allow-expired,n,z
