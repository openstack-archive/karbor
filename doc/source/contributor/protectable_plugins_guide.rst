
=====================================
Protectable Plugins Development Guide
=====================================

.. contents:: :depth: 2

Introduction
============

This Guide provides instructions on how to develop and use your protectable plugins;
the guide also gives an overview of the existing protectable plugins.

Before you read this document, it is recommended to:

#. Deploy an OpenStack environment with the latest Karbor version.
See the `Karbor Installation Guide <https://docs.openstack.org/developer/karbor/installation.html>`_.


Overview
========

The protectable plugin is responsible for the implementation of getting a type of protectable
element which Karbor can protect. Most prominently OpenStack resources (volume, project, server,
etc). The actual instance of protectable element is named Resource. The Protectable Plugin about
one type resource defines what types resource it depend on. It defines the dependency between
different resource type in the default distribution of Karbor.

You can extend the functionality of gettting the Karbor's protectable resources
through implementing new protectable plugins.


Existing Plugins
================
.. toctree::
   :maxdepth: 1

   ../protectable_plugins


Create a protectable plugin
===========================
The Karbor code-base has a python API that corresponds to the set of API calls
you must implement to be a Karbor protectable plugin. Within the source code directory,
look at karbor/service/protection/protectable_plugin.py

A protectable plugin must implement the following methods:

#. get_resource_type: This function will return the resource type that this plugin supports.

#. get_parent_resource_types: This function will return the possible parent resource types.

#. list_resources: This function will list resource instances of type this plugin supported.

#. show_resource: This function will show one resource detail information.

#. get_dependent_resources: This function will be called for every parent resource type.
   For example, a the parent resource types for volume are "server" and "project".
   The method get_dependent_resources will be called once for each.


Add the configuration of the protectable plugin

#. Adding the Plugin class module to the entry_points
   Add the protectable plugin module name to the protection namespace of karbor in the entry_points
   section of setup.cfg file

.. code-block:: ini

    [entry_points]
    karbor.protectables =
    project = karbor.services.protection.protectable_plugins.project:ProjectProtectablePlugin
    server = karbor.services.protection.protectable_plugins.server:ServerProtectablePlugin
    volume = karbor.services.protection.protectable_plugins.volume:VolumeProtectablePlugin
    image = karbor.services.protection.protectable_plugins.image:ImageProtectablePlugin
    share = karbor.services.protection.protectable_plugins.share:ShareProtectablePlugin
    network = karbor.services.protection.protectable_plugins.network:NetworkProtectablePlugin
    database = karbor.services.protection.protectable_plugins.database:DatabaseInstanceProtectablePlugin

