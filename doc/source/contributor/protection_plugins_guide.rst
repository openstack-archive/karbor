
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

====================================
Protection Plugins Development Guide
====================================

.. contents:: :depth: 2

Introduction
============

Protection plugins are one of the core components of Karbor's protection
service. During protect, restore, and delete operations, Karbor is activating
the protection plugins for the relevant resources in a certain order. Each
protection plugin can handle one or more protectables (resource types) and
specifices the actual implementation for them.

Overview
========

Plugins are responsible for the implementation of the following operations, for
each protectable (resource type) they cover:

#. Protect - creating a checkpoint from an existing resource
#. Restore - creating a resource from an existing checkpoint
#. Delete - delete the resource from a checkpoint

Plugins can and should use the bank in order to store protection metadata (and
sometimes the data itself) as part of a protect operations, consume the
metadata from the bank during a restore operation, and delete it the data from
the bank during a delete operation.


Each plugin must implement the following interface:

.. code-block:: python

    class ProtectionPlugin(object):
        def get_protect_operation(self, resource):
            pass

        def get_restore_operation(self, resource):
            pass

        def get_delete_operation(self, resource):
            pass

        @classmethod
        def get_supported_resources_types(cls):
            pass

        @classmethod
        def get_options_schema(cls, resource_type):
            pass

        @classmethod
        def get_saved_info_schema(cls, resource_type):
            pass

        @classmethod
        def get_restore_schema(cls, resource_type):
            pass

        @classmethod
        def get_saved_info(cls, metadata_store, resource):
            pass

#. **get_supported_resources_types**: this method should return a list of
   resource types this plugin handles. The plugin's methods will be called for
   each resource of these types. For example: `OS::Nova::Instance`,
   `OS::Cinder::Volume`.
#. **get_options_schema**: returns a schema of options and parameters for a
   protect operation.
#. **get_saved_info_schema**: returns a schema of data relevant to a protected
   resource in a checkpoint
#. **get_saved_info**: returns the actual data relevant to a protected resource
   in a checkpoint
#. **get_restore_schema**: returns a schema of parameters available for restore
   operation.
#. **get_protect_operation**, **get_restore_operation**,
   **get_delete_operation**: each returns an Operation instance to be used for
   the protect, restore, and delete operations respectively. This instance may
   be created for each resource, or shared between multiple resources.
   The details of the Operation instance will be covered in the following
   sections.


Order of Execution
==================

Karbor's protection service orchestrate the execution of plugin operations, in
relation to the resources the operation is activated on. This is important,
because the order might be very important for some resources in specific
operations. On the other hand, some operations can happen concurrently in order
to speed up the operation. The `get_parent_resource_types` and
`get_dependent_resources` methods from the protectable plugins, define the
relation between two resources.

Examples:

#. In protect operation, a server plugin might want to quiesce the server
   before protecting the volume in order to achieve a certain level of
   consistency for the protected volume. After protecting the volume, we would
   like to unquiesce the server again. However, once the server the volumes are
   attached to is quiesced, multiple volumes can be protected concurrently.
#. In restore operation, we would like to restore the server's base image or
   volume, prior to creating the server itself. However, multiple images and
   volumes can be restored concurrently, as there is no relation between them.

Three phases are defined for each operation:

#. **Preparation Phase**: This phase is for performing actions in relation to a
   resource's dependencies. It's called the "Preparation Phase" because it
   where a plugin should do all the preparation required for the next phase.
   Operation in this phase should be as short as possible since they are not
   parraralized as much as in the following phases. As an example, taking
   snapshots of all the volumes should happen in relation to the owning VMs
   and also happen in a narrower time frame. Copying those snapshots can
   happen later and is much more parallizable.
#. **Main Phase**: This phase is for doing work that has no dependencies or
   time sensitivity. This will be mainly used for transferring the large amount
   of information generated in the backup to different sites.
#. **Completion Phase**: This phase is for performing work once *all* the work,
   not just preparation, was completed on a resource and all of it's
   dependencies. This is a good place to attach resources (in case of restore)
   or close transactions.

As a Protection Plugin developer you would like to minimize the work needed to
be done in the preparation and completion phases and do the bulk of the work in
the main phase since will allow for the most efficient execution of the
operation.

Implementing Plugin Operation
=============================

In order to specify the detailed flow of each operation, a *Protection Plugin*
needs to return an Operation instance implementing 'hooks'. These hooks, differ
from one another by their time of execution in respect to other hooks, either
of the same resource, or other resources. The Operation interface:

.. code-block:: python

    class Operation(object):
        def on_prepare_begin(self, checkpoint, resource, context, parameters,
                             **kwargs):
            pass

        def on_prepare_finish(self, checkpoint, resource, context, parameters,
                              **kwargs):
            pass

        def on_main(self, checkpoint, resource, context, parameters, **kwargs):
            pass

        def on_complete(self, checkpoint, resource, context, parameters,
                        **kwargs):
            pass


It's important to note that it is not necessary to implement every hook. It's
completely valid to only use the main or preparation phase. In fact, only
complex protection plugins are believed to require to do work in all of the
phases.

For *each* operation the plugin can implement each of the hooks:

#. **Preparation hooks**: as noted, preparation is for running tasks in
   relation to other resources in the graph. This is why two hooks exist, one
   for running before dependent resources' preperation and one for after.

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



Existing Plugins
================
.. toctree::
   :maxdepth: 1

   ../protection_plugins
