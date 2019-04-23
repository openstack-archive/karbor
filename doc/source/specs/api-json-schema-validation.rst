..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============
API Validation
==============

https://blueprints.launchpad.net/karbor/+spec/karbor-json-schema-validation

Currently, Karbor has different implementations for validating
request bodies. The purpose of this blueprint is to track the progress of
validating the request bodies sent to the Karbor server, accepting requests
that fit the resource schema and rejecting requests that do not fit the
schema. Depending on the content of the request body, the request should
be accepted or rejected consistently.


Problem description
===================

Currently Karbor doesn't have a consistent request validation layer. Some
resources validate input at the resource controller and some fail out in the
backend. Ideally, Karbor would have some validation in place to catch
disallowed parameters and return a validation error to the user.

The end user will benefit from having consistent and helpful feedback,
regardless of which resource they are interacting with.


Use Cases
=========

As a user or developer, I want to observe consistent API validation and values
passed to the Karbor API server.


Proposed change
===============

One possible way to validate the Karbor API is to use jsonschema similar to
Nova, Keystone and Glance (https://pypi.org/project/jsonschema).
A jsonschema validator object can be used to check each resource against an
appropriate schema for that resource. If the validation passes, the request
can follow the existing flow of control through the resource manager to the
backend. If the request body parameters fails the validation specified by the
resource schema, a validation error wrapped in HTTPBadRequest will be returned
from the server.

Example:
"Invalid input for field 'name'. The value is 'some invalid name value'.

Each API definition should be added with the following ways:

* Create definition files under ./karbor/api/schemas/.
* Each definition should be described with JSON Schema.
* Each parameter of definitions(type, minLength, etc.) can be defined from
  current validation code, DB schema, unit tests, or so on.

Some notes on doing this implementation:

* Common parameter types can be leveraged across all Karbor resources. An
  example of this would be as follows::

    from karbor.api.validation import parameter_types
    # plan create schema
    <snip>
         create = {
            'type': 'object',
            'properties': {
                'type': 'object',
                'plan': {
                    'type': 'object',
                    'properties': {
                        'name': parameter_types.name,
                        'description': parameter_types.description,
                        'provider_id': parameter_types.uuid,
                        'parameters': parameter_types.metadata,
                        'resources': parameter_types.metadata,
                    },
                    'required': ['provider_id', 'parameters'],
                    'additionalProperties': False,
                },
            },
            'required': ['plan'],
            'additionalProperties': False,
        }

    parameter_types.py:

    name = {
        'type': 'string', 'minLength': 0, 'maxLength': 255,
    }

    description = {
        'type': ['string', 'null'], 'minLength': 0, 'maxLength': 255,
        'pattern': valid_description_regex,
    }

    uuid = {
        'type': 'string', 'format': 'uuid'
    }

    # This registers a FormatChecker on the jsonschema module.
    # It might appear that nothing is using the decorated method but it gets
    # used in JSON schema validations to check uuid formatted strings.
    from oslo_utils import uuidutils

    @jsonschema.FormatChecker.cls_checks('uuid')
    def _validate_uuid_format(instance):
        return uuidutils.is_uuid_like(instance)

* The validation can take place at the controller layer using below decorator::

    from karbor.api.schemas import plans as plan

    @validation.schema(plan.create)
    def create(self, req, body):
        """Creates a new plan."


* When adding a new API resources to Karbor, the new resource must be proposed
  with its appropriate schema.


Alternatives
------------

Before the API validation framework, we needed to add the validation code into
each API method in ad-hoc. These changes would make the API method code dirty
and we need to create multiple patches due to incomplete validation.

If using JSON Schema definitions instead, acceptable request formats are clear
and we don't need to do ad-hoc works in the future.


Data model impact
-----------------

None


REST API impact
---------------

API Response code changes:

There are some occurrences where API response code will change while adding
schema layer for them. For example, On current master 'services' table has
'host' and 'binary' of maximum 255 characters in database table. While updating
service user can pass 'host' and 'binary' of more than 255 characters which
obviously fails with 404 ServiceNotFound wasting a database call. For this we
can restrict the 'host' and 'binary' of maximum 255 characters only in schema
definition of 'services'. If user passes more than 255 characters, he/she will
get 400 BadRequest in response.

API Response error messages:

There will be change in the error message returned to user. For example,
On current master if user passes more than 255 characters for volume name
then below error message is returned to user from karbor-api:

Invalid input received: name has <actual no of characters user passed>
characters, more than 255.

With schema validation below error message will be returned to user for this
case:

Invalid input for field/attribute name. Value: <value passed by user>.
'<value passed by user>' is too long.


Security impact
---------------

The output from the request validation layer should not compromise data or
expose private data to an external user. Request validation should not
return information upon successful validation. In the event a request
body is not valid, the validation layer should return the invalid values
and/or the values required by the request, of which the end user should know.
The parameters of the resources being validated are public information,
described in the Karbor API spec, with the exception of private data.
In the event the user's private data fails validation, a check can be built
into the error handling of the validator not to return the actual value of the
private data.

jsonschema documentation notes security considerations for both schemas and
instances:
http://json-schema.org/latest/json-schema-core.html#anchor21

Better up front input validation will reduce the ability for malicious user
input to exploit security bugs.


Notifications impact
--------------------

None

Other end user impact
---------------------

None

Performance Impact
------------------

Karbor will need some performance cost for this comprehensive request
parameters validation, because the checks will be increased for API parameters
which are not validated now.


Other deployer impact
---------------------

None


Developer impact
----------------

This will require developers contributing new extensions to Karbor to have
a proper schema representing the extension's API.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
chenying : <ying.chen@huawei.com>

Work Items
----------

1. Initial validator implementation, which will contain common validator code
   designed to be shared across all resource controllers validating request
   bodies.
2. Introduce validation schemas for existing API resources.
3. Enforce validation on proposed API additions and extensions.
4. Remove duplicated ad-hoc validation code.
5. Add unit and end-to-end tests of related APIs.
6. Add/Update Karbor documentation.

Dependencies
============

None


Testing
=======

Some tests can be added as each resource is validated against its schema.
These tests should walk through invalid request types.

Documentation Impact
====================

1. The Karbor API documentation will need to be updated to reflect the
   REST API changes.
2. The Karbor developer documentation will need to be updated to explain
   how the schema validation will work and how to add json schema for
   new API's.


References
==========

Useful Links:

* [Understanding JSON Schema] (http://spacetelescope.github.io/understanding-json-schema/reference/object.html)

* [Nova Validation Examples] (https://opendev.org/openstack/nova/src/branch/master/nova/api/validation)

* [JSON Schema on PyPI] (https://pypi.org/project/jsonschema)

* [JSON Schema core definitions and terminology] (http://tools.ietf.org/html/draft-zyp-json-schema-04)

* [JSON Schema Documentation] (http://json-schema.org/documentation.html)
