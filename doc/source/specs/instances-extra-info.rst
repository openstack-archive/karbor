..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

===================================================
Add extra_info field for the response of protectable instances API
===================================================

https://blueprints.launchpad.net/karbor/+spec/instances-extra-info

Problem description
===================
We can only query the id, name and type of protectable instance using the restful API
of protectable instance. We can not get more info about the resource instance.
Some other info about instance is also needed when we protect resources with different
resources type.
For example: database instance. only the name of database instance is not enough. The
host ip, the database system name about the instance are also needed.


Use Cases
=========

Scenario #1
User want get the extra info of resource instances from the response of protectable
instances API. Now the protectable instances API only return the id, name and type of
the resource instances.

Scenario #2
User uses the Protectable Instances API to query the info of instances from the vendor's
backup software. User also can save the extra_info of resource instances to the plan,
not only the id, name, type of resources.




Proposed change
===============
Protectable Instances API:
When return a protectable instance, a new field would be available called
``extra-info``.
This field must be a dict in the format of::

        {
                "key1": "value1",
                "key2": "value2",
        }

Keys and values *must* both be strings.
The extra-info of instances is only used for presentation to a user/tenant.
The values in extra-info filed of a resource can not be used inside the protection
service of karbor and protection plugins.

The UI about the extra-info of protectable instances
Show the extra-info in resource tree page. Add a fa-chevron-right icon before the
Logo of the resource. The extra-info of this resource is collapsed by default.
If a user/tenant click the icon, The extra-info will be displayed under this resource.
Click the icon again, the extra-info will be collapsed.

Add a new field extra_info to the response for Protectable Instances API.
  /{project_id}/protectables/{protectable_type}/instances:
    get:
      summary: Resource Instances
      description: |
        Return all the available instances for the given protectable type.
          examples:
            application/json: {
              "instances": [
                {
                  "id": "cb4ef2ff-10f5-46c9-bce4-cf7a49c65a01",
                  "type": "OS::Nova::Server",
                  "name": "My VM",
                  "extra_info": {
                      "hostname": "KarborServer",
                      "availability_zone": "AZOne",
                      "cell_name": "CellOne"
                    }
                  "dependent_resources": [
                    {
                      "id": "99777fdd-8a5b-45ab-ba2c-52420008103f",
                      "type": "OS::Glance::Image",
                      "name": "cirros-0.3.4-x86_64-uec"
                      "extra_info": {
                          "availability_zone": "AZOne",
                          "cell_name": "CellOne"
                      }
                    }
                  ]
                }
              ]
            }

Protectable Plugins can return the extra_info of resource Instances.

The extra_info field in resource database table is only for presentation to a user/tenant.
The values in extra_info field can not be used and modified in karbor protection service.
Add a new field extra_info to resources database table;
 resources
+-------------------------+--------------+------+-----+---------+-------+
| Field                   | Type         | Null | Key | Default | Extra |
+-------------------------+--------------+------+-----+---------+-------+
| id                      | Integer      | NO   | PRI | NULL    |       |
| plan_id                 | varchar(255) | NO   | FOR | NULL    |       |
| resource_id             | varchar(36)  | NO   |     | NULL    |       |
| resource_type           | varchar(64)  | NO   |     | NULL    |       |
| resource_name           | varchar(255) | NO   |     | NULL    |       |
| resource_extra_info     | Text         | NO   |     | NULL    |       |
| created_at              | Datetime     | YES  |     | NULL    |       |
| updated_at              | Datetime     | YES  |     | NULL    |       |
| deleted_at              | Datetime     | YES  |     | NULL    |       |
| deleted                 | Boolean      | NO   |     | NULL    |       |
+-------------------------+--------------+------+-----+---------+-------+



Alternatives
------------

Do nothing, this is not a mission critical feature.

Data model impact
-----------------

None

REST API impact
---------------

Add a new field extra_info to the response for Protectable Instances API.

Security impact
---------------

None

Notifications impact
--------------------

None

Other end user impact
---------------------

The new API will be exposed to users via the python-karborclient.

Performance Impact
------------------

None

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

* Write API
* Add to Karbor client
* Write tests
* Add a usage example for API

Dependencies
============

None


Testing
=======

Unit tests in Karbor and the python-karborclient.


Documentation Impact
====================

Add a usage example for API.


References
==========

None
