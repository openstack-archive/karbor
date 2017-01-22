..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
Restore Resource Status
=======================

https://blueprints.launchpad.net/karbor/+spec/restore-resource-status

Protection plugin should be able to set the status of a restoring resource
during a restore operation. By doing so, users gain visiblity of the restore
process:

- Resources currently being protected
- Resources restored successfully
- Resources whose restore has failed, and the reason for the failure


Problem description
===================

Use Cases
---------

- Giving visibility for the restore process
- Exposing the user to the reason for the failure of a resource restore

Proposed Change
===============

- Add 'resource_status' and 'resource_reason' dictionaries to the Restore object
- Add 'update_resource_status' method to the Restore object
- Protection Plugin should use the 'update_resource_status' to set the status of
  each resource during restore operation


Alternatives
------------

By not adding this, users will have no visibility to resource status during and
after restore operation.

Data model impact
-----------------

- Add 'resource_status' dictionary to Restore object: represents the status of
  the restoring/restored resource
- Add 'resource_reason' dictionary to Restore object: free text representing the
  reason for the restore failure of the resource

REST API impact
---------------

- 'resource_status' dictionary and 'resource_reason' dictionary are added to the
  Restore object

Security impact
---------------

Validation should be imposed on the status set by plugins, and on the reason
text.

Other end user impact
---------------------

python-karborclient and karbor-dashboard should consume the new fields of the
Restore object.

Performance Impact
------------------

Calling 'update_resource_status' sets values in the database which should have
a slight impact on performance.


Other deployer impact
---------------------

Protection plugins should use the new API to set the resource status.

Implementation
==============


Testing
=======


Documentation Impact
====================

- Add 'resource_status' and 'resource_reason' to Restore object
- Add 'update_restore_status' to Protection Plugin writing documentation
