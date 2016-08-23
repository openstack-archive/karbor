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
    </style>

.. role:: red
.. role:: green
.. role:: yellow
.. role:: indigo

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

Protection Plugin Operation Activities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

*Protection Plugin* defines how to protect, restore, and delete resources. In
order to specify the detailed flow of each operation, a *Protection Plugin*
needs to implement numerous 'hooks'. These hooks, named *Activities*, differ
from one another by their time of execution in respect to other activities,
either of the same resource, or other resources. 

#. **PreActivity**: invoked before any activity for this resource and dependent
   resources has begun
#. **ParallelActivity**: invoked after the resource *PreActivity* is complete,
   regardless of the dependent resources' activities.
#. **PostActivity**: invoked after all of the resource's activities are
   complete, and the dependent resources' *PostActivities* are complete

For example, a Protection Plugin for Nova servers, might implement a protect
operation by using *PreActivity* to contact a guest agent, in order to complete
database and operation system transactions, use *ParallelActivity* to backup
the server metadata, and use *PostActivity* to contact a guest agent, in order
to resume transactions.

Practically, the protection plugin may implement methods in the form of::

  activity_<operation_type>_<activity_type>

Where:

* ``operation_type`` is one of: ``protect``, ``restore``, ``delete``
* ``activity_type`` is one of: ``pre``, ``post``, ``parallel``

Notes:

* Unimplemented methods are practically no-op
* Each such method receives as parameters: ``checkpoint``, ``context``,
  ``resource``, and ``parameters`` objects
* These methods may return immediately, or use ``yield``. In the case ``yield``
  is used, the Protection Provider infrastructure is responsible for
  periodically call ``next()``, in order to "poll". This is extremely useful in
  cases where asynchronous operations are initiated (such as Cinder volume
  creation), but polling must be performed in order to decide when the
  operation is complete, and whether it is successful or not. For example:

::

  def activity_protect_parallel(self, checkpoint, context, resource, parameters):
      id = start_operation( ... )
      while True:
          status = get_status(id)
          if status == 'error':
              raise Exception
          elif status == 'success':
              return
          else:
              yield

.. figure:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/activities-links.png
    :alt: Activities Links
    :align: center

    Activities Links

    :green:`Green`: link of the parent resource PreActivity to the child
    resource PreActivity

    :yellow:`Yellow`: link of the resource PreActivity to ParallelActivity

    :red:`Red`: link of the resource ParallelActivity to PostActivity

    :indigo:`Indigo`: link of the child resource PostActivity to the parent
    resource PostActivity

This scheme decouples the tree structure from the task execution. A plugin that
handles multiple resources or that aggregates multiple resources to one task can
use this mechanism to only return tasks when appropriate for it's scheme.

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/pluggable_protection_provider.svg
    :alt: Karbor
    :align: center

References
==========
1. `Class Diagram Source <http://raw.githubusercontent.com/openstack/karbor/master/doc/images/specs/pluggable_protection_provider.pu>`_
2. `Dependency graph building algorithm <https://docs.google.com/document/d/1Mkd9RgUVdiRL6iei8Nqzzx4xteKIcd-yjMLEkV4Jc9s/edit#>`_
