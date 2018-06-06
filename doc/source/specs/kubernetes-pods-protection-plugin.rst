..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=============================================================================
The kubernetes pod with persistent volumes protectable and protection plugins
=============================================================================

https://blueprints.launchpad.net/karbor/+spec/kubernetes-pods-protection-plugin

Problem description
===================

With the rapid development of cloud computing, there is a trend of explosive growth in cloud
data over recent years. Cloud data backup and recovery has become an urgent topic which the
customers concern. Running Kubernetes on OpenStack becames more and more popular. The data
protection of the application on Kubernetes also need be considered.

In this spec we would like to introduce a plugin in Karbor to protect your application deployed
in Kubernetes which runs on top of OpenStack. The application data protected by Karbor include
the configurations and metadata in etcd service, and the persistent volume provided by Cinder.


Use Cases
=========

The kubernetes cluster can run on openstack instances using Openstack cloud provider, the pods
can be created with persistent volumes provided by Cinder. This bp adds kubernetes pods with
persistent volumes protection plugin in Karbor.

Proposed change
===============

The kubernetes pod protectable plugin:
--------------------------------------
A new protectable plugin about The kubernetes pod need be implemented.
The type of resource the kubernetes pod is "OS::Kubernetes::Pod". It will be added to the constant
RESOURCE_TYPES in Karbor.


1. The parent resource types: PROJECT_RESOURCE_TYPE

2. list the resources:

   This interface of plugin will call the 'list_pod_for_all_namespaces' API method in the
   kubernetes python client[1].

3. show the resource:

   This interface of plugin will call the 'read_namespaced_pod' method API method in the
   kubernetes python client. The parameter is a pod id.

4. get dependent resources:

   The parameter parent_resource is a project, this interface of plugin will return the
   kubernetes pod in this project.

The volume protectable plugin:
------------------------------
1. Add a new parent resource types: "OS::Kubernetes::Pod"

2. get dependent resources:

   The parameter parent_resource is a kubernetes pod, this interface of plugin will return the
   persistent volumes list provided by Cinder in the this parent resource pod.


The kubernetes pod protection plugin
------------------------------------
A new protection plugin about the kubernetes pod need be implemented.

1. Protect Operation:
   The configurations and metadata in etcd service about the pod will be saved to
   the bank of Karbor.

2. Restore Operation:
   The persistent volumes of the pod will be restored by Cinder Volume plugins.

   Get the configurations and metadata in etcd service about the pod from bank, and create
   a new pod with restored persistent volumes from cinder in the kubernetes cluster.

3. Delete Operation:

   The configurations and metadata about the pod will be deleted from the bank.
   The backup data of persistent volumes will be deleted from Cinder.

The kubernetes pod protection plugin schema:
--------------------------------------------

::

    OPTIONS_SCHEMA = {
        "title": "The kubernetes pod Protection Options",
        "type": "object",
        "properties": {
            "backup_name": {
                "type": "string",
                "title": "Backup Name",
                "description": "The name of the kubernetes pod backup."
            },
            "description": {
                "type": "string",
                "title": "Description",
                "description": "The description of the kubernetes pod backup."
            }
        },
        "required": ["backup_name", "description"]
    }

    RESTORE_SCHEMA = {
        "title": "The kubernetes pod Protection Restore",
        "type": "object",
        "properties": {
            "restore_name": {
                "type": "string",
                "title": "Restore Name",
                "description": "The name of the restored kubernetes pod.",
                "default": None
            },
            "restore_description": {
                "type": "string",
                "title": "Restore Description",
                "description": "The description of the restored kubernetes pod.",
                "default": None
            }
        }
    }


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

None

Other deployer impact
---------------------

Add the kubernetes pod protection plugin endpoint to setup.cfg.
Add the kubernetes pod protection plugin configuration to provider file.


Developer impact
----------------

None


Implementation
==============

Assignee(s)
-----------


Work Items
----------

* Write kubernetes pod backup protectable plugin
* Write kubernetes pod backup protection plugin
* Write tests
* Add a usage example about kubernetes pod protection

Dependencies
============

None


Testing
=======

Unit tests in Karbor.


Documentation Impact
====================

Add a usage example about kubernetes pod protection.


References
==========

[1] https://github.com/kubernetes-incubator/client-python
