Globus Action Provider - Python SDK
=====================================

This SDK is a Python toolkit to help developers create Action Providers for use
in `Globus <https://www.globus.org>`_ Automate or for invocation via Globus
Flows.

This toolkit is experimental and no support is implied for any sort of use of
this package. It is published for ease of distribution among those planning
to use it for its intended experimental purpose.


Introduction
============

The fundamental purpose of the Globus Automate platform is to tie together
multiple operations or units of work into a coordinated orchestration. We refer
to each of these operations as an *Action*. In particular, the *Flows* service
provides a means of coordinating multiple actions across potentially long
periods of time to perform some aggregate function larger than any single Action
provides. The *Triggers* service ties *Events*, or occurrences within a managed
environment, to Actions such that each occurrence of the Event automatically
invokes the Action associated with it.

In both the Flows and the Triggers cases, the Actions require a uniform
interface for invocation, monitoring and possibly termination so that new
Actions may be introduced without requiring customization or re-implementation
of the invoking services. We refer to the service endpoints which can be invoked
in this manner as *Action Providers* and the uniform interface for interacting
with the Action Providers as the *Action Provider Interface*. This toolkit
facilitates the creation of custom Action Providers which can be invoked
throughout the Globus Automate platform.

.. toctree::
   :maxdepth: 2

   action_provider_interface
   setting_up_auth
   installation
   toolkit
   examples
   changelog
   license
