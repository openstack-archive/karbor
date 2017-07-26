
============
Introduction
============

What is Karbor?
===============

Karbor is an OpenStack project that provides a pluggable framework for
protecting and restoring Data and Metadata that comprises an OpenStack-deployed
application - Application Data Protection as a Service.


Mission Statement
-----------------
To protect the Data and Metadata that comprises an OpenStack-deployed
Application against loss/damage (e.g. backup, replication) by providing a
standard framework of APIs and services that allows vendors to provide plugins
through a unified interface


Typical Use Case: 3-Tier Cloud App
==================================

3-Tier Cloud App Web/App/DB

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/3-tier-app.png
    :alt: 3-Tier Cloud App
    :width: 600
    :align: center

In order to provide full Protection for this typical use case, we would have to
protect many resources, which have some dependency between them. The following
diagram demonstrates how this dependency looks, in the form of a tree:

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/resource_tree_architecture.png
    :alt: Resource Tree
    :width: 600
    :align: center

These resources can be divided into groups, each of which will be handled by a
different plugin in Karbor:

-  Volume
-  VM
-  Network
-  Project
-  Images

Main Concepts
=============

Protection Providers
--------------------

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/
    protection_provider.png
    :width: 600

Protection providers are defined by the administrator for each tenant. The
encapsulate every aspect of the protection procedure, namely, where to place
the backup metadata and the data and how to do it. From the tenants perspective
as long as it has access to a provider it should be able to set up replication,
back up data, and restore data.

Since there could be many protection providers with varied features and options
each protection provider exposes what options it provides for each protectable.
This allows the UI to dynamically adapt to each provider and show the user what
options are available, what they mean and what values are supported.

This allows us to extend the providers without updates to Karbor and allow
provider implementation to easily add specialize options.

Example
~~~~~~~

Let’s take the OpenStack::Cinder::Volume resource *Protect* action.

One of the action parameters in the Parameters Schema will be
"Consistency Level"::

    "parameters_schema" : {
        "type": "object",
        "properties": {
            "consistency_level": {
                "title": "Consistency Level",
                "description": "The preferred consistency level",
                "enum": ["Crash", "OS", "Application"]
            }
        }
    }

Protection Plans
----------------

Protection plan encapsulate all the information about the protection of the
project. They define what you want to protect, what protection provider
will be used for this plan, and what specialized options will be passed to the
provider.

There are two main aspect to protection plan. The first is the continuous
aspect. When a plans is started it becomes enabled and continues protection
processes are started and monitored (eg. replication). As long as the plan is
active Karbor will try and make sure the continuous aspects are active and valid.

The other aspect is point in time protection or, as we call them in Karbor,
checkpoints. Checkpoints are saved in the protection provider paired with the
plan and, as stated, represent a restorable point in time for the plan. When a
checkpoint is created Karbor will store in the protection provider all the
information required to successfully restore the project covered by the plan
to how it was at that specific point in time.

Automatic Operation
-------------------
Automatic operations are process that the user want to perform without manual
intervention. Up until now we described how to manually manage plans and
checkpoints. The user can start and suspend plans and create and delete backups
manually whenever it wants. This is perfect for small scale deployments but
most administrators will want to have these operations automated. As an example
they would like to set up checkpoints every day or disable replication over
the weekend when the system is not in use.

Automatic operations are varied and their features vary by operation type.
There are simple operation like "back up plan" which creates a single
checkpoints at the user requested time or even. And there are more complex
automatic operations like the RetentionPlan which allows the user to define a
complex retention plan to automate the creation and deletion of checkpoints.

Protectables
------------
Protectables are any class or type of entity that can be protected by Karbor.
Since setups might have different entities they would like to protect Karbor
doesn't bind the API to specific entity types. The admin can even add new
protectables during set up as long as the protection provider can handle those
entities. This flexibility means that Karbor is agnostic to the relationship
between the resources being backed up.

