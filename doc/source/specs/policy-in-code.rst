..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
Policy in code
==============

https://blueprints.launchpad.net/karbor/+spec/policy-in-code

The oslo.policy library now supports handling policies in a way similar to
how oslo.config handles config options. We can switch our policy handling
to keep default policy settings in the code, with the policy file only
necessary for overriding the defaults.

By having default policies in code, this allows:

#. Simplified deployment and upgrades since config files don't need to change
   that don't modify defaults.
#. Easier maintenance of policy files since they only have overridden policies.
#. A programmatic way to generate policy documentation and samples similar to
   how we handle config options.


Problem description
===================

There have been bugs in the past from either new features adding the wrong
policy settings, or for getting policy settings all together. For admins it
can also be difficult configuring policies due to many policy settings that
are never changed making locating the desired setting harder.

This would simplify our policy.json file by only needing to have those entries
that differ from the defaults. It would also allow us to generate a sample
policy file similar to how we do for karbor.conf to show all the possible
settings with the defaults commented out for easy reference.

Use Cases
=========

As a deployer I would like to configure only policies that differ from the
default.

Proposed change
===============

Starting with oslo.policy 1.9.0 [0], policies can be declared in the code with
provided defaults and registered with the policy engine.

Any policy that should be checked in the code will be registered with the
policy.Enforcer object, similar to how configuration registration is done.
Any policy check within the code base will be converted to use a new
policy.Enforcer.authorize method to ensure that all checks are defined. Any
attempt to use a policy that is not registered will raise an exception.

Registration will require two pieces of data:

1. The rule name, e.g. "plan:get"
2. The rule, e.g. "rule:admin_or_owner" or "role:admin"

The rule name is needed for later lookups. The rule is necessary in order to
set the defaults and generate a sample file.

A third optional description can also be provided and should be used in most
cases so it is available in any generated sample policy files.

We can then use this code to add a job that will generate a sample policy.json
file showing the commented out defaults directly from the code base.

[0] https://github.com/openstack/oslo.policy/blob/1.9.0/doc/source/usage.rst#registering-policy-defaults-in-code

Alternatives
------------

Stick with our manually configured policy file that has no checks or full
reference for possible policy enforceable settings.

Data model impact
-----------------

None.

REST API impact
---------------

None.

Security impact
---------------

None. Although this touches our policy handling, this just enables preemptive
policy checks and does not change the way we handle policy enforcement.

Notifications impact
--------------------

None.

Other end user impact
---------------------

None.

Performance Impact
------------------

There will be slightly more work done at service startup time as policies are
registered, which should be a very small impact. Policy checking at run time
may become slightly faster due to having a smaller policy file to read before
each check.

Other deployer impact
---------------------

End user admins will no longer need to have all settings defined in the
policy.json file, only those that they want different than the defaults.

Developer impact
----------------

Any policies added to the code should be registered before they are used.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  chenying

Work Items
----------

* Define and register all policies.
* Switch policy checks to use new method.
* Update Devstack to not expect policy.json file.
* Update deployer documentation.
* Update tox genconfig target to also generate sample policy file.

Dependencies
============

Current requirements are for oslo.policy >= 1.9.0, so no extra dependencies
are required.

Testing
=======

If done correctly, no additional or different testing should be required.
Existing tests should detect if there are any changes in the expected policy
behavior.

Documentation Impact
====================

Documentation should be updated to state that only policies which are changes
to the default policy will be needed when configuring policy settings.

Updates will also be made to our devref documentation describing the process
for generating the sample policy file.

References
==========

None.
