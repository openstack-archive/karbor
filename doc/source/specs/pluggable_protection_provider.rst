..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

.. raw:: html

    <style>
        .red {color:#d32f2f; font-weight: bold;}
        .green {color:#4caf50; font-weight: bold;}
        .yellow {color:#fbc02d; font-weight: bold;}
        .indigo {color:#536dfe; font-weight: bold;}
        .purple {color:#cd12da; font-weight: bold;}
        .black {color:#000000; font-weight: bold;}
    </style>

.. role:: red
.. role:: green
.. role:: yellow
.. role:: indigo
.. role:: purple
.. role:: black

==========================================
Pluggable Protection Provider
==========================================

https://blueprints.launchpad.net/karbor/+spec/protection-plugin-is-design

Protection Provider
===================

Protection Provider is a user-facing, configurable, pluggable entity, that
supplies the answer for the questions: "how to" and "where to". By composing
different bank-store (responsible for the "where to") and different *Protection
Plugins* (each responsible for the "how to"). The Protection Provider is
configurable, both in the terms of bank and protection plugins composition, and
in their configuration.

The protection provider will contain internally, a map between any registered
*Protectable* (OpenStack resource type) and a corresponding *Protection
Plugin*, which is used for operations related to any appropriate resource.

There are 3 resource operations a *Protection Provider* supports, and any
*Protection Plugin* needs to implement. These operations usually act on
numerous resources, and the *Protection Provider* infrastructure is responsible
for using the corresponding *Protection Plugin* implementation, for each
resource. The *Protection Provider* is responsible for initiating a DFS traverse
of the resource graph, building tasks for each of the resources, and linking
them in respect of the execution order and dependency.

#. **Protect**: the protection provider will traverse the selected resources
   from the resource graph
#. **Restore**: the protection provider will traverse the resource graph saved
   in the checkpoint
#. **Delete**: the protection provider will traverse the resource graph saved
   in the checkpoint

After the entire graph has been traversed, the Protection Provider will return
the task flow which will be queued and then executed according to the
executor's policy. When all the tasks are done the operation is considered
complete.

Protection Provider Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Protection Providers are loaded from configuration files, placed in the
directory specified by the ``provider_config_dir`` configuration option (by
default: ``/etc/karbor/providers.d``). Each provider configuration file must
bear the ``.conf`` suffix and contain a ``[provider]`` section. This section
specifies the following configuration:

#. ``name``: the display name of the protection provider
#. ``id``: unique identifier
#. ``description``: textual description
#. ``bank``: path to the bank plugin
#. ``plugin``: path to a protection plugin. Should be specified multiple times
   for multiple protection plugins. Every *Protectable* **must** have a
   corresponding *Protection Plugin* to support it.

Additionally, the provider configuration file can include other section
(besides the ``[provider]`` section), to be used as configuration for each bank
or protection plugin.

For example::

  [provider]
  name = Foo
  id = 2e0c8826-81d6-44f5-bbe5-8f46a98c5845
  description = Example Protection Provider
  bank = karbor.protections.karbor-swift-bank-plugin
  plugin = karbor.protections.karbor-volume-protection-plugin
  plugin = karbor.protections.karbor-image-protection-plugin
  plugin = karbor.protections.karbor-server-protection-plugin
  plugin = karbor.protections.karbor-project-protection-plugin

  [swift_client]
  bank_swift_auth_url = http://10.0.0.10:5000
  bank_swift_user = admin
  bank_swift_key = password

Protection Plugin
=================

A *Protection Plugin* is a component responsible for the implementation of
operations (protect, restore, delete) of one or more *Protectable* (i.e
resource type). When writing a *Protection Plugin*, the following needs to be
defined:

#. Which resources does the protection plugin support
#. What is the schema of parameters for each operation
#. What is the schema of information the protection plugin stores in a
   Checkpoint
#. The implementation of each operation

Protection Plugin API & Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Protection Plugin* defines how to protect, restore, and delete resources.

When performing an operation there might be a need for a ProtectionPlugin to
perform actions on a resource before or after some operation was performed on
a related resource.

For example, before takin a spanshot of a volume you need to quiesce the VM
and\or run any guest agent operation. Doing it after taking the checkpoint is
useless.

On the other hand, when copying a volume's data to different sites there is no
need for other operations to wait on the copy.

Finally, there might be a need to perform an operation marking a transaction
as successful after everything related to a VM was protected.

Looking at this we see there are 3 distinct phases for every protection.

#. *Preparation Phase*: This phase for performing actions in relation to a
   resource's dependencies. It's called the "Preparation Phase" because it
   where a plugin should do all the preparation required for the next phase.
   Operation in this phase should be as short as possible since they are not
   parraralized as much as in the following phases. As an example, taking
   snapshots of all the volumes should happen in relation to the owning VMs
   and also happen in a narrower time frame. Copying those snapshots can
   happen later and is much more parallizable.
#. *Main Phase*: This phase is for doing work that has no dependencies or time
   sensitivity. This will be mainly used for transferring the large amount of
   information generated in the backup to different sites.
#. *Completion Phase*: This phase is for performing work once *all* the work,
   not just preparation, was completed on a resource and all of it's
   dependencies. This is a good place to attach resources (in case of restore)
   or close transactions.

As a Protection Plugin developer you want to minimize the work needed to be
done in the preparation and completion phases and do the bulk of the work in
the main phase since will allow for the most efficient execution of the
operation.

It's important to note that a developer doesn't have to do any action during a
phase. It's completely valid to only use the main or preparation phase. In
fact, we think it's going to be very rare that a Protection Plugin will need
to use all the phases.

In order to specify the detailed flow of each operation, a *Protection Plugin*
needs to implement numerous 'hooks'. These hooks, differ from one another by
their time of execution in respect to other hooks, either of the same
resource, or other resources.

For *each* operation the pluggin can implement each of the hooks:

#. **Preparation hooks**: as noted, preparation is for running tasks in
   relation to other resources in the graph. This is why two hooks exist, one
   for running before dependent resources' pereperation and one for after.

   #. **Prepare begin hook**: invoked before any hook of this resource and
      dependent resources has begun.

      For tasks that need to happen before any dependent resource’s operations
      begin

      Hook method name: **on_prepare_begin**

   #. **Prepare finish hook**: invoked after any prepare hooks of dependent
      resources are complete.

      For tasks that finish the work began in *prepare begin hook*, for tasks that
      require that the dependent resource’s prepare phase finished

      Hook method name: **on_prepare_finish**

#. **Main hook**: invoked after the resource *prepare hooks* are complete.

   For tasks that do heavy lifting and can run in parallel to dependent or
   dependee resources *main hooks*

   Hook method name: **on_main**

#. **Complete hook**: invoked once the resource's main hook is complete, and
   the dependent resources' *complete hooks* are complete

   For tasks that require that the dependent resource's operations are
   complete, and finalize the operation on the resource.

   Hook method name: **on_complete**

For example: a Protection Plugin for Nova servers, might implement a protect
operation by using *prepare begin hook* to quiesce the Server and/or contact a
guest agent to complete transactions. A protection plugin for Cinder volumes
can implement *prepare finish hook* to take a snapshot of the volume. The
server's *prepare finish hook* unquiesces the server and/or contacts a guest
agent. Both the server's and the volume's *main hook* do the heavy lifting of
copying the data.

Notes:

* Unimplemented methods are practically no-op
* Each such method receives as parameters: ``checkpoint``, ``context``,
  ``resource``, and ``parameters`` objects

::

  def prepare_finish(self, checkpoint, context, resource, parameters):
      ...

.. figure:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/hooks.png
    :alt: Protection Plugin Hooks
    :align: center

    Protection Plugin Hooks

    :green:`Green`: Child resource Prepare_begin depends on its parent resource
    Prepare_begin

    :indigo:`Indigo`: The resource Prepare_finish depends on the resource
    Prepare_begin

    :purple:`Purple`: Parent resource Prepare_finish depends on the child
    resource Prepare_finish

    :yellow:`Yellow`: The resource Main depends on the resource Prepare_finish

    :red:`Red`: The resource Complete depends on the resource Main

    :black:`Black`: Parent resource Complete depends on the child resource’s
    Complete



This scheme decouples the tree structure from the task execution. A plugin that
handles multiple resources or that aggregates multiple resources to one task can
use this mechanism to only return tasks when appropriate for it's scheme.

References
==========
1. `Class Diagram Source <http://raw.githubusercontent.com/openstack/karbor/master/doc/images/specs/pluggable_protection_provider.pu>`_
2. `Dependency graph building algorithm <https://docs.google.com/document/d/1Mkd9RgUVdiRL6iei8Nqzzx4xteKIcd-yjMLEkV4Jc9s/edit#>`_
