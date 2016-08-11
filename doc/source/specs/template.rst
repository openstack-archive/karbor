..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Example Spec - The title of your RFE
====================================

Include the URL of your launchpad RFE:

https://bugs.launchpad.net/karbor/+bug/example-id

Introduction paragraph -- why are we doing this feature? A single paragraph of
prose that **deployers, and developers, and operators** can understand.

Do you even need to file a spec? Most features can be done by filing an RFE bug
and moving on with life. In most cases, filing an RFE and documenting your
design is sufficient. If the feature seems very large or contentious, then
you may want to consider filing a spec.


Problem description
===================

A detailed description of the problem. What problem is this blueprint
addressing?

Use Cases
---------

What use cases does this address? What impact on actors does this change have?
Ensure you are clear about the actors in each use case: Developer, End User,
Deployer etc.

Proposed Change
===============

How do you propose to solve this problem?

This section is optional, and provides an area to discuss your high-level
design at the same time as use cases, if desired.  Note that by high-level,
we mean the "view from orbit" rough cut at how things will happen.

This section should 'scope' the effort from a feature standpoint: how is the
'Karbor end-to-end system' going to look like after this change? What Karbor
areas do you intend to touch and how do you intend to work on them?


Alternatives
------------

What other ways could we do this thing? Why aren't we using those? This doesn't
have to be a full literature review, but it should demonstrate that thought has
been put into why the proposed solution is an appropriate one.

Data model impact
-----------------


REST API impact
---------------


Security impact
---------------

Describe any potential security impact on the system.  Some of the items to
consider include:

Other end user impact
---------------------

Performance Impact
------------------

Describe any potential performance impact on the system, for example
how often will new code be called, and is there a major change to the calling
pattern of existing code.

Examples of things to consider here include:

* A periodic task might look like a small addition but if it calls conductor or
  another service the load is multiplied by the number of nodes in the system.

* Scheduler filters get called once per host for every instance being created,
  so any latency they introduce is linear with the size of the system.

* A small change in a utility function or a commonly used decorator can have a
  large impacts on performance.

* Calls which result in a database queries (whether direct or via conductor)
  can have a profound impact on performance when called in critical sections of
  the code.

* Will the change include any locking, and if so what considerations are there
  on holding the lock?


Other deployer impact
---------------------

Discuss things that will affect how you deploy and configure OpenStack
that have not already been mentioned, such as:

* What config options are being added? Should they be more generic than
  proposed (for example a flag that other hypervisor drivers might want to
  implement as well)? Are the default values ones which will work well in
  real deployments?

* Is this a change that takes immediate effect after its merged, or is it
  something that has to be explicitly enabled?

* If this change is a new binary, how would it be deployed?

Implementation
==============

Assignee(s)
-----------

Who is leading the writing of the code? Or is this a blueprint where you're
throwing it out there to see who picks it up?

If more than one person is working on the implementation, please designate the
primary author and contact.

Primary assignee:
  <launchpad-id or None>

Other contributors:
  <launchpad-id or None>

Work Items
----------

Work items or tasks -- break the feature up into the things that need to be
done to implement it. Those parts might end up being done by different people,
but we're mostly trying to understand the timeline for implementation.


Dependencies
============

* Include specific references to specs and/or blueprints in Karbor, or in other
  projects, that this one either depends on or is related to.

* If this requires functionality of another project that is not currently used
  by Nova (such as the glance v2 API when we previously only required v1),
  document that fact.

* Does this feature require any new library dependencies or code otherwise not
  included in OpenStack? Or does it depend on a specific version of library?


Testing
=======


Documentation Impact
====================


References
==========

Please add any useful references here. You are not required to have any
reference. Moreover, this specification should still make sense when your
references are unavailable. Examples of what you could include are:
