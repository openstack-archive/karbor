============
Architecture
============

High Level Architecture
=======================
.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/
    high_level_architecture.png
    :alt: Solution Overview
    :width: 600
    :align: center

The system is built from independent services and a scalable *Workflow
engine* that ties them together:

API Service
===========

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/
    karbor-api.png
    :width: 600

These top-level north-bound APIs expose Application Data Protection services to
the Karbor user.

The purpose of the services is to maximize flexibility and accommodate for
(hopefully) any kind of protection for any type of resource, whether it is a
basic OpenStack resource (such as a VM, Volume, Image, etc.) or some ancillary
resource within an application system that is not managed in OpenStack (such as
a hardware device, an external database, etc.).


Resource (Protectable) API
--------------------------

Enables the Karbor user to access information about which resource types are
protectable (i.e. can be protected by Karbor).  In addition, enables the user to
get  additional information on each resource type, such as a list of actual
instances and their dependencies.

Provider API
------------

Enables the Karbor user to list available providers and get parameters and
result schema super-set for all plugins of a specific Provider.

Plan API
--------

This API enables the Karbor user to access the protection Plan registry and do
the following operations:

-  Plan CRUD.
-  List Plans.
-  Starting and suspending of plans.

Automatic Operation API
-----------------------

This API enables the Karbor user to manage protection Operations:

-  Create a checkpoint for a given Protection Plan.
-  Delete unneeded checkpoints from the provider.
-  Query the status on a given Operation ID.

Checkpoint API
--------------

This API enables the Karbor user to access and manage checkpoints stored in
the protection provider:

-  List all checkpoints given a Bank ID.
-  Show Information on a given checkpoint ID.
-  Delete a checkpoint.
-  Create a checkpoint.

Restore API
-----------

This API enables the Karbor user to restore a checkpoint onto a restore target:

-  Create restored system from a checkpoint.

Operation Engine Service
========================

This subsystem is responsible for scheduling and orchestrating the execution of
*Protection Plans*.

The implementation can be replaced by any other external solution since it uses
only functions that are available through the north-bound API.

Once an entity is created, it can be tracked through the north-bound API,
so monitoring the operations is independent from the scheduler.

It will be responsible for the automatic execution of specific operations
and tracking them.

Automatic Operation
-------------------

Automatic operations are the core of the scheduler. They define higher level
automatic logic. A simple scenario is a set of scheduled operations that
perform basic APIs at a specific trigger. There will also be complex scheduling
policies available that perform multiple north-bound basic APIs.

Trigger Engine
--------------

This sub-component of the schedule service is responsible for generating
triggers, which begin the execution of the Plan Orchestration.

It can be done based on a timer or an event collector, based on implementation.

In the first Karbor reference implementation, the trigger engine will only
provide time-based triggers.

Scheduled Operation
-------------------

This sub-component of the schedule service is responsible for holding the
mapping between a trigger and operation(s).

Protection Service
==================

This subsystem is responsible for handling the following tasks:

-  Operation Execution
-  Protection Provider management

WorkFlow Engine
---------------

This pluggable component is responsible for executing and orchestrating the
flow of the plan across all protection providers.
