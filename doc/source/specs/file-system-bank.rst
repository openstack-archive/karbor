..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
File System based Bank implementation
==========================================

https://blueprints.launchpad.net/karbor/+spec/file-system-bank

Problem description
===================

Currently we only suppport Swift as a bank implementation. This means that
anyone that uses Karbor must also install Swift. This might be unacceptable or
over complicated for some deployments. Furthe more, having a many options
for bank backends is always a good things.

I suggest adding an FS based implementation. It will use files for
objects storing objects and object metadata.

Use Cases
=========

As explained, deployers might not want or will be unable to install Swift in
their cloud.

Proposed change
===============

Objects would be stored under a file name with their ID having `/` be defined
as a directory separator.

For example::
        Object ID: /checkpoints/2fd14f87-46bd-43a9-8853-9e1a84ebee3d/index.json

Since object names might contain chars that are unavailable as regular files
we will need to escape some chars so that they can be used as file names.

We propose the following encoding escape sequence
non ascii chars would be modified to `%[XX..]` where XX are Hex
representations of the utf-8 encodinf of the characters.

This avoids using back-slash for escape.


Example::
        object*with%wierd*id
        =>
        object%[2A]with%[25]wierd%[2A]id

The metadata files will be in a JSON format. The name and format of these files
are same as the meatadata objects in the swift bank.

For example::
        /checkpoints/3a4d76e7-f8d8-4f2f-9c1d-107d88d7a815/ <- directory
        /checkpoints/3a4d76e7-f8d8-4f2f-9c1d-107d88d7a815/metadata <- md file
        /checkpoints/3a4d76e7-f8d8-4f2f-9c1d-107d88d7a815/status


Alternatives
------------

Do nothing, this is not a mission critical feature.

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
