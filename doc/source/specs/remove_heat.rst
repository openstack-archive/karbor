..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===========
Remove Heat
===========

https://blueprints.launchpad.net/karbor/+spec/remove-heat

Problem description
===================

As it stands, Karbor uses Heat to restore the resources which had been protected
before. Although it works well, some disadvantages are still very obvious. Firstly,
Karbor just uses a fraction of functions which Heat supplies so that it seems too
heavy to Karbor. Second, for developers of protection plugins, they prefer implementing
the restoration of resources by protection plugin itself to Heat. Third, both Karbor
and Heat should be deployed at the time, which will add more workload. Last, from
the point of view of implementation, Heat stack runs after all the protection
plugins' hooks which breaks the hook definition of 'on_complete'.


Use Cases
=========

* Implement restoration of resources by protection plugins themselves.
* No longer deploy Heat.


Proposed change
===============

There are two main changes. First one, the implementation of restore should be
refactored for all protection plugins. At present, there are 4 kinds of plugins
in Karbor and the new restore methods are described as below respectively.

* volume plugin
  It will create a new volume with original backup volume.

* image plugin
  It will create a new image and upload the original backup data to it.

* network plugin
  It will create a new network with original backup network.

* vm plugin
  It is a bit more complex, because it has several child resources, such as volume, ip.
  First, it should create a new vm. Second, add the child resources to it, such as
  attach the volumes, set the ip.

Another change is updating the deployment scripts which will no longer install Heat.


Alternatives
------------

None

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

There should be no loss on performance, because it does same work as Heat actually.

Other deployer impact
---------------------

None

Developer impact
----------------

The developers of protection plugins should know these changes.


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* refactor all protection plugins
* update the deployment scripts
* update the document of developing protection plugin

Dependencies
============

None

Testing
=======

Unit and fullstack tests in Karbor.


Documentation Impact
====================

Documents about how to develop protection plugin should be updated also.

References
==========

None
