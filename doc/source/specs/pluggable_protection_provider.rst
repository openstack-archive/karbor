..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Pluggable Protection Provider
==========================================

https://blueprints.launchpad.net/smaug/+spec/operation-engine-design

Problem Description
===================

Even though we allow each provider to be implemented in any way it pleases we
foresee that most providers will want to be able share code between them.
We would also like for a user to be able to easily extend the ProtectionProvider
that will be provided by default.

Proposed Change
===============

As as solution we propose the *Pluggable Protection Provider*.

The *Pluggable Protection Provider* will be the reference implementation
protection provider. It's purpose is to be fully pluggable and extandable so
that only extream use cases will need to implement their own Protection Provider
from scratch.

The protection provider will contain internally a map between any registered
*Protectable* and a corrosponding *Protection Plugin*. When the pluggable
protection provider is asked to perform an action, it will walk over the
graph and pass a context object to the appropriate plugin whenever a node is
encountered.

The resource graph is traversed in with DFS. When a node is first encountered
the protection manager gets the plugin for the appropriate resource type, builds
a context and passes it to the plugins `get_pre_task()` method. The plugin can
return any tasks that it wants added to the task list. When all of a node
childrens have been visited the `get_pre_task()` is called. The task returned
from this method will also be added to the task list but is also guranteed to
execute after all the child node's tasks have finished. Any of the methods can
return `None` if they don't want any action performed.

After the entire grap has been traversed the Protection Provider will return
the task lists which will be queued and than executed according to the
executor's policy. When all the tasks are done the operation is considered
complete.

This scheme decouples the tree structure form the task execution. A plugin that
handles multiple resources or that aggregates mutiple resources to one task can
use this mechanism to only return tasks when appropriate for it's scheme.

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/pluggable_protection_provider.svg
    :alt: Smaug
    :align: center

References
==========
1. `Class Diagram Source <http://raw.githubusercontent.com/openstack/smaug/master/doc/images/specs/pluggable_protection_provider.pu>`_
2. `Dependency graph building algorithm <https://docs.google.com/document/d/1Mkd9RgUVdiRL6iei8Nqzzx4xteKIcd-yjMLEkV4Jc9s/edit#>`_
