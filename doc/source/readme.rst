.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/Smaug.png
    :alt: Smaug
    :align: center

What is Smaug?
==============

Smaug is an OpenStack project that provides a framework for Application
Data Protection as a Service.

It is named after the famous dragon from J.R.R. Tolkien's The "Hobbit",
which was known to hoard and guard the treasures of the people.

Mission & Scope
===============

Formalize Application Data Protection and Disaster recovery in OpenStack
(APIs, Services, Plugins ...)

Be able to protect Any Resource in OpenStack(as well as their
dependencies)

Allow Diversity of vendor solutions, capabilities and implementations
without compromising usability.

Typical Use Case: 3-Tier Cloud App
==================================

3-Tier Cloud App Web/App/DB

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/
    3-tirApp.png
    :alt: 3-Tier Cloud App
    :width: 600
    :height: 455
    :align: center

In order to provide full Protection for this typical use case, we would
have to protect many resources, which have some dependency between them.
The following diagram demonstrates how this dependency looks, in the
form of a tree:

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/
    resource_tree_architecture.png
    :alt: Resource Tree
    :width: 600
    :height: 455
    :align: center

These resources can be divided into groups, each of which will be
handled by a different  plugin in Smaug:

-  Volume
-  VM
-  Network
-  Project
-  Images

Main Concepts
=============

Protection Providers
-----------------------

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/
    protection_provider.png

Protection providers are defined by the administrator for each tenant. The
encapsulate every aspect of the protection procedure, namely, where to place
the backup metadata and the data and how to do it. From the tenants perspective
as long as it has access to a provider it should be able to set up replication,
back up data, and restore data.

Since there could be many protection providers with varied features and options
each protection provider exposes what options it provides for each protectable.
This allows the UI to dynamically adapt to each provider and show the user
what options are available, what they mean and what values are supported.

This allows us to extend the providers without updates to Smaug and allow
provider implementation to easily add specialize options.

Example
=======

Let’s take the OpenStack::Cinder::Volume resource *Protect* action.

One of the action parameters in the Parameters Schema will be
"Consistency Level":

.. code-block:: JSON

      "parameters_schema" : {
            "type": "object",
            "properties": {
                "consistency_level": {
                    "title": "Consistency Level",
                    "description": "The preferred consistency level",
                    "enum": [ "Crash", "OS", "Application" ]
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
active Smaug will try and make sure the continuous aspects are active and valid.

The other aspect is point in time protection or, as we call them in Smaug,
checkpoints. Checkpoints are saved in the protection provider paired with the
plan and, as stated, represent a restorable point in time for the plan. When a
checkpoint is created Smaug will store in the protection provider all the
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
Protectabes are any class or type of entity that can be protected by Smaug.
Since setups might have different entities they would like to protect Smaug
doesn't bind the API to specific entity types. The admin can even add new
protectables during set up as long as the protection provider can handle those
entities. This flexibility means that Smaug is agnostic to the relationship
between the resources being backed up.

High Level Architecture
=======================
.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/
    high_level_architecture.png
    :alt: Solution Overview
    :width: 600
    :height: 455
    :align: center

The system is built from independent services and a scalable *Workflow
engine* that ties them together:

Smaug API Service
=================

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/
    smaug-api.png

These top-level north-bound APIs expose Application Data Protection
services to the Smaug user.

The purpose of the services is to maximize flexibility and accommodate
for (hopefully) any kind of protection for any type of resource, whether
it is a basic OpenStack resource (such as a VM, Volume, Image, etc.) or
some ancillary resource within an application system that is not managed
in OpenStack (such as a hardware device, an external database, etc.).


Resource (Protectable) API
---------------------------

Enables the Smaug user to access information about which resource types are protectable (i.e. can be protected by Smaug).
In addition, enables the user to get  additional information on each resource type, such as a list of actual instances and their dependencies.

Provider API
---------------

Enables the Smaug user to list available providers and get parameters and result schema super-set for all plugins of a specific Provider.

Plan API
--------

This API enables the Smaug user to access the protection Plan registry
and do the following operations:

-  Plan CRUD.
-  List Plans.
-  Starting and suspending of plans.

Automatic Operation API
--------------------------

This API enables the Smaug user to manage protection Operations:

-  Create a checkpoint for a given Protection Plan.
-  Delete unneeded checkpoints from the provider.
-  Status on a given Operation ID.

Checkpoint API
---------------

This API enables the Smaug user to access and manage the checkpoints stored
in the protection provider:

-  List all checkpoints given a Bank ID.
-  Show Information on a given checkpoint ID.
-  Delete a checkpoint.
-  Create a checkpoint.

Restore API
---------------

This API enables the Smaug user restore a checkpoint on to a restore target:

-  Create restored system from a checkpoint.

Smaug Schedule Service
======================

This subsystem is responsible for scheduling and orchestrating the
execution of *Protection Plans*.

The implementation can be replaced by any other external solution since it
uses only functions that are available through the north-bound API.

Once an entity is created it can be tracked through the north-bound API as well
so that monitoring the operations is independent from the scheduler.

It will be responsible for executing the automatic operations to specific
tasks and tracking  them.

Automatic Operation
-------------------

Automatic operations are the core of the scheduler. They define higher level
automatic logic. The simple case are scheduled operations that perform basic
operations at a specific trigger. There will also be available complex
scheduling policies that will perform multiple north-bound basic APIs.

Trigger Engine
--------------

This sub-component of the Schedule Service is responsible for generating
triggers to begin the execution of the Plan Orchestration.

It can be done based on a Timer or an Event Collector - Open to
implementation.

In the first version of Smaug reference implementation, it will only
provide time-based triggering.

Scheduled Operation
-------------------

The sub-component of the Schedule Service is responsible for holding the
mapping between a Trigger and Operation(s).

Smaug Protection Service
========================

This subsystem is responsible for handling the following tasks:

-  Operation Execution
-  Protection Provider management

WorkFlow Engine
---------------

This pluggable component is responsible for executing and orchestrating
the flow of the plan across all protection providers.

Communication and Meetings
==========================

Smaug Launchpad Link\ https://launchpad.net/smaug

Smaug Code Review\ https://review.openstack.org/#/q/smaug+status:open,n,z

Smaug Code Repository\ https://github.com/openstack/smaug

Smaug daily IRC Channel: #openstack-smaug

Smaug bi-weekly IRC Meeting on (even) Tuesday at 1400 UTC in #openstack-meeting
at freenode:\ http://eavesdrop.openstack.org/#Smaug_Project_Meetingtion(s).

Smaug Trello Board\ https://trello.com/b/Sudr4fKT/smaug

Additional references
-----------------------
`Tokyo summit talk  <http://www.slideshare.net/gampel/openstack-tokyo-talk-application-data-protection-service>`_
`Smaug overview slide <https://docs.google.com/presentation/d/1JYO1VIlTkGTF6lvKEMcsHkaST3mYFxuarpcNTJ3HBhk/edit?usp=sharing>`_
`Smaug Overview blog  <http://blog.gampel.net/2015/12/smaug-application-data-protection-for.html>`_
