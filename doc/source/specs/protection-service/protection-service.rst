..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

====================================
Protection Service Basics
====================================

https://bugs.launchpad.net/karbor/+bug/1529199

Protection Service is a component of karbor (an openstack project working as a
service for data protection), which is responsible to execute
protect/restore/other actions on operations (triggered plans).

Architecturally, it acts as a RPC server role for karbor API service to actually
execute the actions on triggered operations.

It's also the role who actually cooperates with protection plugins provided by
providers.  It will load providers (composed by a series of plugins) and thus
manage them.

Internally, protection service will construct work flow for each operation
action execution, where tasks in work flow will be linked to a graph by
resource dependency and thus be executed on parallel or linearly according to
the graph task flow.

RPC interfaces
================================================

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/protection-architecture.png

From the module graph, protection service basically provide following RPC
calls:

Operation RPC:
--------------------
**execute_operation(backup_plan:BackupPlan, action:Action):** where action
could be protect or restore

Provider RPC:
-------------
**list_providers(list_options:dict): []Providers:**

**show_provider(provider_id:String}:Provider**

Checkpoint RPC:
---------------

**list_checkpoints(list_options:{}): []Checkpoints**

**show_checkpoint(provider_id:String, checkpoint_id:String): Checkpoint**

**delete_checkpoint(provider_id:String, checkpoint_id:String):void**

Main Concept
============
.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/class-diagram.png


Protection Manager
------------------
Endpoint of the RPC server, which will handle Operation RPC calls and dispatch
other RPC calls to corresponding components.

It will produce a graph work flow for each operation execution, and have the
work flow to be executed through its work flow engine.

ProviderRegistry
----------------

Entity to manage multiple providers, which will load provider definitions on
init from config files and maintain them in memory map.

It will actually handle RPC related to provider management, like
list_providers() or show_provider().

CheckpointCollection
--------------------

Entity to manage checkpoints, which provides CRUD interfaces to handle
checkpoint. As checkpoint is a karbor internal entity, one checkpoint operation
is actually composed by combination of several BankPlugin atomic operations.

Take create_checkpoint as example, it will first acquire write lease (there
will be detailed **lease** design doc) to avoid conflict with GC deletion, then
it needs create key/value for checkpoint itself. After that, it will build
multiple indexes for easier list checkpoints.

Typical scenario
======================================
A typical scenario will start from a triggered operation being sent through RPC
call to Protection Service.

Let's take action protect as the example and analyze the sequence together with
the class graph:

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/protect-rpc-call-seq-diagram.png

1. Karbor **Operation Engine**
------------------------------
who is responsible for triggering operation according to time schedule or
events, will call RPC call of Protection Service:
execute_operation(backup_plan:Bac,upPlan, action:Action);

2. ProtectionManager
------------------------
who plays as one of the RPC server endpoints, and will handle this RPC call by
following sequence:

2.1 CreateCheckpointTask:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This task will be the start point task of the graph flow. This task will call
the unique instance of class
**Checkpoints**:create_checkpoint(plan:ProtectionPlan), to create one
checkpoint to persist the status of the action execution.

The instance of **Checkpoints** will retrieve the **Provider** from input
parameter **BackupPlan**, and get the unique instance of **BankPlugin**.

While **BankPlugin** provides interfaces for CRUD key/values in **Bank** and
lease interfaces to avoid write/delete conflict, **Checkpoints** is responsible
for the whole procedure of create checkpoint, including grant lease,
create key/value of checkpoint, build indexes etc. through composing calls to
**BankPlugin**

2.2 Call ProtectionProvider to build the resource flow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This task is built by walking through **resource tree** (see
**Pluggable protection provider** doc), which will return a graph flow.
The result graph flow is composed of tasks representing the activities of the
ProtectionPlugin for each resource, and the links between the tasks according
to the activities type, and resource dependencies.

The graph flow returned by ProtectionProvider would be added to the top layer
task flow, right behind the start point task **CreateCheckpointTask**, and will
be executed with parallel engine.

The protection plugin is responsible for storing the ProtectionData (backup
id, snapshot id, image id, etc) into the Bank under the corresponding
**ProtectionDefinition**.

2.3 CompleteCheckpointTask
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This task is added into the top layer task flow right after the task flow built
form ProtectProvider, which will be executed only when all tasks ahead of it
have been completed successfully. This task will update the checkpoint status
to be available, and commit it to the bank.
