..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=================
Bank Plugin Basic
=================
Bank Plugin is a component of karbor (an openstack project working as a
service for data protection), which is responsible for execute CRUD actions in
Bank.

The bank is a backend (such as swift) which is used to store the metadata/data
of protection plan. Here, we take swift as an bank implementation example.

******
leases
******
Karbor will create a checkpoint when protecting a protection plan. This
checkpoint is maintained with status, which is a enum type: protecting,
available, restoring, deleted, etc.

The status is used for karbor API layer to control access to one checkpoint from
users.

With the 'protecting' status, there're two cases which we can't tell the
difference:

1. The protection service is working and those 'protecting' protection plan are
   being executed;

2. When the Protection Service crashes, those 'protecting' protection plan are
   actually zombie ones, and those checkpoints are zombie ones too;

In the second case, we need a garbage collection component (GC) to cleanup those
zombie checkpoints.

In order to tell whether the checkpoint is a zombie or not, we introduce a lease
mechanism based on bank plugin.

Here, we take swift as an example. The lease is stored as an object in swift
with the characteristics of auto-deleted.

The owner of one checkpoint will periodically refresh the expire time of the
lease object key.

When the protection service crashes, the leases of bank plugins will be
auto-deleted by the swift-object-expirer(one service of swift).

When GC comes to check whether one checkpoint is a zombie to be collected, GC
will first get the owner of the checkpoint. Then it will check whether the lease
of the owner exists.

If the lease exists, those 'protecting' checkpoints can not be deleted by the
GC; otherwise the GC will cleanup them.

Granularity
===========
To avoid flood to bank server, we don't keep one lease for per checkpoint.
Instead, we keep one lease per checkpoint owner. So the granularity of lease is
per bank plugin instance.

When one protection service instance gets initialized, each bank plugin instance
will get initialized as well. Each bank plugin will start to maintain its own
leases with its corresponding bank server.

Here, every bank plugin will play a role as lease client while the bank server
(swift cluster) plays as the lease server.

Functions
=========
acquire_lease
-------------
Each bank plugin (lease client) will use this function to acquire a lease from
bank server (lease server).

For swift specifically, it will create a lease object in swift container and set
an expire_window for this lease.

The expire_window represents the validity of this lease from creation
(or latest-renew) until being auto-deleted by swift server. The value of
expire_window should be configurable.

We use owner_id to identify one instance of bank plugin. The owner_id is a uuid
created when bank plugin instance is initiated, say, generated from sha256 with
parameter as hostname and the timestamp instance initiated.

The key of lease object stored in swift looks like this:
/account/leases/owner_id.

In order to map one checkpoint to its owner, we will create an index like this:
/account/checkpoints/checkpoint_id/owner when creating a checkpoint.

- create_owner_id: create a uuid to represent this bank plugin instance
- put_object: use swift-client to create a lease object in swift, and set
  'X-Delete-After' as: expire_window
- set_expire_time in memory in lease client side: set the expire_time as:
  now+expired_time

renew_lease
-----------
This function will be called by each lease client in the background
periodically.

The renew_window represents the period with which the lease client will refresh
lease frequently. This renew_window is configurable as well, where
renew_window < expire_window.

If lease client succeeds to renew lease, this lease has a new expire_window in
lease server from now on. Then the lease client side will update the expire_time
in memory with value as: expire_time = now + expired_window.

If lease client fails to renew, this lease object keeps the old expire_window in
lease server side. The lease client won't update its expire_time in memory.

- post_object: use swift-client to reset the 'X-Delete-After' header as:
  expired_window
- update_expire_time: if post_object succeeds, update expire_time as:
  now+expired_window; otherwise, don't refresh the expire_time.

check_lease_validity
--------------------
This function is used by the checkpoint owner to check whether there is enough
time to execute an
update operation to one checkpoint (or anything else guarded by the lease)
before the lease expiring.

We use validity_window to represent the time window inside which an update
operation to a checkpoint should complete.  This window is configurable and
should be estimated by admin.

This function will check if validity_window <= expire_time - now.  If it's true,
this function will return true and thus allow update operation to go ahead;
otherwise, this function will return false and the update operation will abort.

Although the lease may haven't expired when
validity_window <= expire_time - now, there might not be enough time to finish
the update operation.  If we allow the update operation to go ahead under this
situation, there is a risk that while the operation is still on-going, the
lease has been recycled by lease server during this period.

check_lease_existence
---------------------
This function is used by GC to check whether the lease object exists or not in
lease server side.

Specifically for checkpoints, GC will scan all checkpoints in 'protecting'
status. It will first get the owner of a checkpoint through its index, and then
check the existence of the lease object in lease server.  If the lease object
doesn't exist, it will take this checkpoint as zombie and go ahead to recycle
it. Otherwise, it will skip this checkpoint and leave it there.

Configurations
==============

renew_window
------------
- represents the period with which lease client will renew the lease in
  background.

expire_window
-------------
- represents how long this lease from creation or latest-renew to expire in
  lease server side.
- Note: expired_window > renew_window.  To make renew mechanism more robust,
  we recommend to set expired_window = N*renew_window.  With this setting, we
  allow (N-1) times failure to renew lease to tolerate unstable network case or
  IO scheduling issue;

validity_window
---------------
- an optional configuration; The default value it set according to the
  renew_window, validity_window <= renew_window
- the window estimated by admin, how long one update operation will take at
  most.  The constraint here should be: validity_window < expire_window.
- Note: Same background as renew_window setting, to allow (N-1) times failure
  of renew lease, we recommend to set validity_window <= renew_window.
