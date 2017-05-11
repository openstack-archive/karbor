..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================================
Restore design spec (protection service level)
==============================================

https://bugs.launchpad.net/karbor/+bug/1560826

Protection Service is a component of karbor (an openstack project working as a
service for data protection), which is responsible to execute
protect/restore/other actions on operations (triggered plans).  The restore
functionality of protection service is basically about 4 aspects:

1. Restore from what point of data

2. How those resources will look like after restoration

3. In which way we will organize the restoration work.

4. How to watch restoration procedure.

The most important assumption we hold here is that the bank of karbor, which
holds our protection data, is high available and reliable.

Restore from what point
================================================

In `document protection service design <https://raw.githubusercontent.com/openstack/karbor/master/doc/source/spes/protection-service/protection-service.rst>`_
, we have described the procedure to protect resource, where for each protection
plan execution, we will persist a checkpoint in bank.

If the checkpoint is in status available, the checkpoint is qualified to be a
foundation where we can build our restoration.

Checkpoint including following data:

Plan:
--------------------
This item is the plan which used to be executed and thus produced this
checkpoint.

Resource dependency graph:
----------------------------------
The resource
dependency graph describes the resource stack set in the plan, and the dependency
among them and their sub resources.

This resource dependency graph will help us to check the resources dependency in
retrospect.

This view is critical since the dependency may vary, e.g., the volume could be
attached or detached to a server time by time.  However, what we aim to rebuild
is the resources stack with same/similar dependency of the original resource
stack at the time point of protection.

Resource definition data:
------------------------------
Resource definition data is the data defined and persisted by each protection
plugin, where protection plugin could persist the metadata of the protection
resource, say, backup id, or the original resource, even the data to be backed
up/replicated.

Those resource definition data could be retrieved during restoration, and could
be parameters to rebuild our resources stack.

Restore to what
===============
The target of restoration is to rebuild the resources stack, which are explicitly
 set or implied in the protection plan.

It means that the resources stack to be protected and rebuilt not only includes
the target resources explicitly set in the protection plan, but also includes
those resources which the target resources depend on.

The karbor protection service will call protection plugin to build the resource
stack in the order of  the dependencies described by the resource graph
(persisted in checkpoint as mentioned above).

However, for each kind of resource, to keep what unchanged but what changed is
not the responsibility of karbor protection service.  It's the implementation of
each protection plugin who is free to define their own rules. Say, one server
protection plugin may require to keep fixed ip unchanged after restoration, and
another server protection plugin may require to keep the attachment device path
of one volume to be the same, etc.  Those requirements could be met in the
implementation of the concrete server protection plugin.

The procedure of building openstack resource stack is aligned with openstack
heat service.  To avoid repeating development work, for now, karbor adopts the
way to generate the heat template (HOT) as the restore intermediate target.
Karbor restore API enables user to specify the file path to export heat template,
and karbor protection service will generate heat template according to protection
data, and will export it to the specified file path.

How to restore
==============
Based on our BaseProtectionPlugin, protection plugin implementation with
single task doesn't need care about task flow building but only needs implement
the restore() function.

options to implement ProtectionPlugin restore()
--------------------------------------------------

Basically, the standard protection plugin restore is to generate heat resource
in memory, but we also tolerates some other backup protection plugin which
doesn't rely on standard openstack API to create resources.  In this way, the
restore function may produce resources directly instead of by heat.

.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/class_diagram.png

Generally, each restore task will share an injected parameter: an instance of
HeatTemplate class.  It's created per restore request, and will manage the in
memory heat template, which will aggregate the in memory HeatParameter instances
and in memory HeatResource instances produced by each restore task.

To tolerate non-standard openstack API based protection plugin, there're two
options to implement restore() function:

**1. Restore() to build in memory HeatParameter instance(s):**

The restore() function will directly build the corresponding resource,wait
until it to be available synchronously.  It then encapsulate the built resource
into HeatParameter object and call heatTemplate.put_parameter(original_id,
heatParameter) to put it for its parent task reference.  The original_id is
the resource id of the protected resource, where parent task could refer it
through this id.

**2. Restore() to build in memory HeatResource instance(s):**

The restore() function won't build resource directly, but only encapsulate an in
memory HeatResource object with protected data as parameter, or refer its
children HeatResource/HeatParameter.  Same as option 1, it will call
heatTemplate.put_parameter(original_id, heatParameter) to put it for its
parent task reference.  The original_id is the resource id of the protected
resource, where parent task could refer it through this id.

Note for **composite resource protection plugin**, say, Network protection plugin,
which is represented as single resource node in resource graph.  However, it
actually builds multiple resources inside its restore() call.  It's required to
generate multiple HeatResource/HeatParameter instances in memory and put
them to shared input HeatTemplate instance.

How to handle resource references between restore tasks:
--------------------------------------------------------

**1. Parent node takes care of attachment**

As the resource graph generated during protection,  the parent node should
take care of the attachment of its children resources.  Say, it's server
protection plugin's work to create attachment resource to attach volumes.

**2. Task flow engine ensures ordering of reference**

Our in memory HeatResource/HeatParameter instances are built based on the
resource graph, and thus even with on parallel task execution, it's guaranteed
by task flow engine that children tasks will be executed first.  Thus the
children HeatResource/HeatParameter instances will be put into an internal
collection before HeatResource/HeatParameter instances produced by parent task.

**3. Refer child resource by original resource id**

To implement restore() function, each resource needs refer their new built
children resources, either by get_param or by get_resource.  As each HeatParam
and HeatResource instance is put into HeatTemplate instance, indexed by the
original id (protected resource id),  parent task could refer its children
HeatParam/HeatResource through the original resource id: by calling
HeatTemplate.get_resource_reference(original_id:String), which will return the
reference object, which could be a resource_id (String) or a dict ({
get_resource: resource_id}).  Note here we give up standard requires/provides to
pass input/output among tasks, since for composite resource like Network, the
HeatParameter/HeatResource it produces is not corresponding to the resource node
it presents.)

**4. Limitation of child resource reference**

If the parent resource protection plugin adopts option 1 to rebuild
resource, and if its child resource protection plugin chooses to follow option2
to rebuild resource, one limitation here is that the parent resource protection
plugin may have no way to refer its child resource since the child resource
won't get generated during the life time of the task.
Considering this limitation, the protection plugin with option1 implementation
could choose to extend heat resource to include its own resource building logic.

work flow of restoration:
-----------------------------
.. image:: https://raw.githubusercontent.com/openstack/karbor/master/doc/images/protection-service/restore-processing-sequence-flow.png


1. User calls API to specify restore from one checkpoint and other restore
params (export heat template file path, external network etc.).

2. In protection service, we retrieve the resource graph from checkpoint;

3. Walk through the resource graph and thus build the task flow of restoration;

4. Execute the restoration task flow, which will dump HeatTemplate with pyyaml
to a temporary file. The file object iss the output of the task graph;

5. Protection service will construct a task dependent on task graphs on step3,
which will be executed to take the heat template as input. It will call heat
client to execute this template.

6. There could be another task to track restoration status as well.

How to restore between two unsymmetrical openstack sites(TBD)
=============================================================
Unsymmetrical caseincluding unsymmetrical physical network, vlan to vxlan,
different server flavor, different volume type, etc.

The basic idea is the protection plugin is free to generate template according
to the target site status.  It could check target site status through openstack
API or config file, and karbor could define some rules to adapt one world to
another.

Restore heat stack managed resources(TBD)
==========================================
The basic idea here is to iterate the
original source template, and look up corresponding resource in protection
checkpoint, and thus rebuild the source template with checkpoint data.  In this
way, the rebuilt resource are still managed by heat stack.

How to watch restoration procedure(TBD)
========================================
The basic idea is to watch corresponding heat stack.
