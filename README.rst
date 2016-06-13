=====
Smaug
=====

Application Data Protection as a Service for OpenStack

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/Smaug.png
    :alt: Smaug
    :width: 300
    :height: 525
    :align: center


*****************
Mission Statement
*****************

To protect the Data and Metadata that comprises an OpenStack-deployed
Application against loss/damage (e.g. backup, replication) by providing a
standard framework of APIs and services that allows vendors to provide plugins
through a unified interface

Open Architecture
"""""""""""""""""

Design for multiple perspectives:

* User: Protect App Deployment

  * Configure and manage custom protection plans on the deployed resources
    (topology, VMs, volumes, images, …)

* Admin: Define Protectable Resources

  * Decide what plugins protect which resources, what is available for the user
  * Decide where users can protect their resources

* Vendors: Standard API for protection products

  * Create plugins that implement Protection mechanisms for different OpenStack 
    resources

*****
Links
*****

* Free software: Apache license
* Documentation: http://docs.openstack.org/developer/smaug
* Source: http://git.openstack.org/cgit/openstack/smaug
* Bugs: http://bugs.launchpad.net/smaug

.. image:: https://raw.githubusercontent.com/openstack/smaug/master/doc/images/SmaugInPieces.png
    :alt: Smaug
    :width: 200
    :height: 525
    :align: center

********
Features
********

Version 0.1
"""""""""""

* Resource API
* Plan API
* Bank API
* Ledger API
* Cross-resource dependencies

Limitations
***********

* Only 1 Bank plugin per Protection Plan
* Automatic object discovery not supported

