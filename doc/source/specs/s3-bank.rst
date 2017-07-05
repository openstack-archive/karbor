..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
File System based Bank implementation
==========================================

https://blueprints.launchpad.net/karbor/+spec/s3-bank-plugin

Problem description
===================

Currently we suppport Swift and File System as bank implementations. We
should increase more bank plugin types so that users will have more choices
to feet their needs in different scenarios.

S3 compatible storage is a valid choice, which is used by many individuals
and companies in the public or private clouds. With S3 based implementation,
it will store objects and object metadata on S3 compatible Storage.

Use Cases
=========

As explained, deployers who want or will use S3 compatible storage in their
cloud.

Proposed change
===============

Objects would be stored under a object name with their ID having `/` be
defined as a separator.

For example::
    Object ID: /checkpoints/2fd14f87-46bd-43a9-8853-9e1a84ebee3d/index.json

The metadata files will be in a JSON format. The name and format of these
files are same as the meatadata objects in the Swift bank.

For example::
    /checkpoints/3a4d76e7-f8d8-4f2f-9c1d-107d88d7a815/ <- directory
    /checkpoints/3a4d76e7-f8d8-4f2f-9c1d-107d88d7a815/metadata <- md file
    /checkpoints/3a4d76e7-f8d8-4f2f-9c1d-107d88d7a815/status


Alternatives
------------

Do nothing, this is not a mission critical feature.


Technical details
-----------------

Related docs:

Amazon S3 REST API Introduction
* http://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html

The python client module that could be used is botocore
* https://github.com/boto/botocore

Data model impact
-----------------

None.

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

This API might be faster\slower than Swift depending on use case.

Other deployer impact
---------------------

None

Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
Pengju Jiao <jiaopengju@cmss.chinamobile.com>

Work Items
----------

* Write Bank Plugin
* Add documentation

Dependencies
============

None


Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

New docs to explain how to use and configure the alternative Bank
implementation.


References
==========

None
