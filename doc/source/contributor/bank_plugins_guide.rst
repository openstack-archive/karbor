
==============================
Bank Plugins Development Guide
==============================

.. contents:: :depth: 2

Introduction
============

This Guide provides instructions on how to develop and use your bank plugins;
the guide also gives an overview of the existing bank plugins.

Before you read this document, it is recommended to:

#. Deploy an OpenStack environment with the latest Karbor version.
See the `Karbor Installation Guide <https://docs.openstack.org/developer/karbor/installation.html>`_.


Overview
========

The bank plugin is responsible for persisting data between protect and restore
operations, and between different sites. This gives Karbor the flexibility store metadata
in many locations, object stores such as Swift, document stores such as MongoDB, relational
databases such as MariaDB, etc.

So a simplified object store interface of bank is defined for most backends to support
saving the metadata and backup data of the checkpoints.

You can extend the functionality of the Karbor's bank through implementing new bank plugins.


Existing Plugins
================
.. toctree::
   :maxdepth: 1

   ../bank_plugins


Create a bank plugin
====================
The Karbor code-base has a python API that corresponds to the set of API calls
you must implement to be a Karbor Bank plugin. Within the source code directory,
look at karbor/service/protection/bank_plugin.py

A bank plugin usually consists of code to:

#. Lists: This function will list all the object from the default container of the bank backend.

#. Creates: This function will create or update one object to the default container of the bank backend.

#. Gets: This function will get one object from the default container of the bank backend.

#. Deletes: This function will delete one object from the default container of the bank backend.


In order to tell whether the checkpoint (saved in the bank) is a zombie or not, a lease mechanism is
introduced to the bank plugin.

* `The detail about the bank plugin lease <https://github.com/openstack/karbor/blob/master/doc/source/specs/bank-plugin-lease.rst>`_.

The bank plugin will play a role as lease client while the bank bankends server
(i.e swift cluster) plays as the lease server. So the bank plugin for a lease server
should consist of code to:

#. acquire_lease
   The bank plugin (lease client) will use this function to acquire a lease from
   bank server (lease server). For swift specifically, it will create a lease object
   in swift container and set an expire_window for this lease.

#. renew_lease
   This function will be called by each lease client in the background periodically.

#. check_lease_validity
   This function is used by GC to check whether the lease object exists or not in
   lease server side.


Add the configuration of the bank plugin

#. Adding the Plugin class module to the entry_points
   Add the bank plugin module name to the protection namespace of karbor in the entry_points
   section of setup.cfg file::

    [entry_points]
    karbor.protections =
    karbor-swift-bank-plugin = karbor.services.protection.bank_plugins.swift_bank_plugin:SwiftBankPlugin
    karbor-fs-bank-plugin = karbor.services.protection.bank_plugins.file_system_bank_plugin:FileSystemBankPlugin


#. The bank plugin can be used by karbor. Before starting the karbor-protection service,
   The admin need to configure the bank plugin entry point name to the configuration of the provider
   (/etc/karbor/providers.d/openstack-fs-bank.conf), Let us take local fs bank plugin as a example::

    [provider]
    name = OS Infra Provider with local file system bank
    description = This provider uses local file system as the bank of karbor
    id = 6659007d-6f66-4a0f-9cb4-17d6aded0bb9
    plugin=karbor-volume-protection-plugin
    bank=karbor-fs-bank-plugin


