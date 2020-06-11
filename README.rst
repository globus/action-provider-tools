Action Provider Tools Introduction
==================================

This is an experimental toolkit to help developers build Action Providers for
use in Globus Automate including for invocation via Globus Flows.

As this is experimental, no support is implied or provided for any sort of use
of this package. It is published for ease of distribution among those planning
to use it for its intended, experimental, purpose.

This README is intended to introduce the concepts, requirements and overview of
this toolkit to be used when implementing an Action for use with Globus
Automate. The three main sections are:

1) an introduction to the interface required of all Actions, 
2) A description of how to prepare your service to use Globus Auth 
3) A description of the content of this toolkit and how it can be used in a
   Python implementation.

This overview does not provide any guidance on how to host or operate the Action
so that it is accessible via the internet.


Actions Overview
================
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
with the Action Providers as the *Action Provider Interface*. We provide here an
overview of the *Action Provider Interface* as a guide for use when implementing
an *Action Provider*. 

The Action Provider Interface
-----------------------------

The Action Provider Interface is a RESTful model for starting, monitoring,
canceling and removing state  associated with the invocation of an Action.
Following the REST resource life-cycle pattern, each Action invocation returns
an identifier representing the invocation (an *Action Instance*). This
identifier is used to monitor the progress of the Action Instance via further
REST calls until its completion, or it may be used to request cancellation of
the instance.

Because the interface is intended to support arbitrary Action types, we
recognize that some Action instances may be long-running (asynchronous) such as
the execution of a computational job. Other Actions may be short-running
(synchronous), able to return their final result directly in response to their
invocation request as is the case in typical RESTful models. The Action
Life-cycle described below specifically supports these execution modes as well
as handling failures and Actions which may be, temporarily, unable to make
progress.

Action Life-cycle
^^^^^^^^^^^^^^^^^

The Life-cycle of an Action defines the set of states that the Action may be in,
and how it can  transition among the states. The states are defined as follows:

*  ``ACTIVE``: The Action is executing and is making progress toward completion

* | ``INACTIVE``: The Action is paused in its execution and is not making
    progress toward completion. Out-of-band (i.e. not via the Action Provider
    Interface) measures may be required to allow the Action to proceed.

* | ``SUCCEEDED``: The Action reached a completion state which was considered
    "normal" or not due to failure or other unrecoverable error. 

* | ``FAILED``: The Action is in a completion state which is "not normal" such as
    due to an error condition which is not considered recoverable in any manner. 

* | ``RELEASED``: The Action Provider has removed the record of the existence of
    the Action.  Further attempts to interact with the Action will be errors as if
    the Action had never existed. All resources associated with the Action may have
    been deleted or removed. This is not a true state in the sense that the state
    can be observed, but ultimately all Actions will be released and unavailable for
    further operations. Any subsequent references to the Action, e.g. via the API
    methods described below, will behave as if the Action never existed.

Upon initial creation of an Action (see operations below), the Action may be in
any of the first four states. If it is in an ``ACTIVE`` or ``INACTIVE`` state,
the Action is considered "asynchronous" and further queries to get the state of
the Action may return updated information. If the Action is in a the
``SUCCEEDED`` or ``FAILED`` states, the Action is synchronous, all information
about the Action is returned on the creation operation and no changes to the
state are possible.

An asynchronous Action may change state between ``ACTIVE`` and ``INACTIVE``
during its life time, and may update further details about its progress while
in either of these states. When a completed state of ``SUCCEEDED`` or ``FAILED``
is reached, the Action state cannot be updated further. The Action Provider is,
however, required to maintain this final state for some period of time so that
the client of the Action may retrieve the completion state. Upon completion, the
client may request that the Action be "released" or the Action Provider may do
so on its own after the required time-out occurs. To save server resources, it
is preferred that the client release the Action when it has reliably retrieved
and processed the final state.

Action Provider Interface and Document Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The primary purpose of the Action Provider Interface is to securely support and
report Actions progressing through the life-cycle described above. The document
types supporting this are the initial Action invocation *Action Request*
document, and the *Action Status* document which contains the life-cycle status
described above along with additional detailed status information specific to
the type of Action being executed.

.. note:: 
    Below, we describe URL paths where operations can be performed. We assume that
    all of these share a common "Base URL" which we don't name in this document. The
    Base URL may be at any place in the URL path namespace desired by the Action
    Provider, and so may be used in conjunction with any other service URLs it may
    support.

.. note:: 
    For brevity and clear presentation, in the descriptions of document types in
    the following  sections, we present the key concepts, but do not enumerate
    every option or field on the documents. Refer to the toolkit components,
    including the OpenAPI format specification (as described in the toolkit
    section), for a complete definition.

Starting an Action: The Action Request Document and the ``POST /run`` Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Starting an Action is performed by making a REST ``POST`` request to the path
``/run`` containing an Action Request document. The request document contains
the following fields:

* | ``request_id``: A client-generated Identifier for this request. A user may
    re-invoke the ``/run`` method with the same ``request_id`` any number of times,
    but the Action must only be initiated once. In this way, the user may re-issue
    the request in case it cannot be determined if a request was successfully
    initiated for example due to network failure.

* | ``body``: An Action Provider-specific object which provides the input for
    the Action to be performed. The ``body`` must conform to the input
    specification for the Action Provider being invoked, and thus the client must
    understand the requirements of the Action Provider when providing the value of
    the ``body``. Thus, the Action Provider must provide documentation on the format
    for the ``body`` property.

* | ``manage_by`` and ``monitor_by``: Each of these is a list of principal
    values in `URN format <https://docs.globus.org/api/search/#principal_Urns>`_,
    and they allow the user invoking the Action to delegate some capability over the
    Action to other principals. ``manage_by`` defines the principals who are allowed
    to attempt to change the execution of the Action (see operations ``/cancel`` and
    ``/release`` below) while it is running. ``monitor_by`` defines principals which
    are allowed to see the state of the Action before its state has been destroyed
    in a release operation. In both cases, the Globus Auth identity associated with
    the ``/run`` operation is implicitly part of both the ``manage_by`` and
    ``monitor_by`` sets. That is, the invoking user need not include their own
    identity into these lists.

Any request to the ``/run`` method which contains an Action Request which
adheres to the input schema will return an Action Status document as described
in the next section. 

Monitoring and Completing an Action: The Action Status Document and Management Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All information about an Action is contained in the Action Status document which
is returned on almost all operations related to an Action (the exception is the
log operation which is optional and is described briefly below). Notable fields
of the Action Status document include:

* | ``action_id``: The unique identifier for this particular action. The
    ``action_id`` may be any string, and it should be treated as an opaque value
    (that is, having no semantic or implied meaning) by the client. The client will
    first learn of an Action's ``action_id`` in the Action Status returned by the
    ``/run`` method.

* | ``status`` and ``display_status``: These provide the description of the
    state of the Action. ``status`` is the specific life-cycle value as described
    above. ``display_status`` is an optional field the Action Provider may supply
    which gives a short text description of the status using language which is
    specific to the Action.
     
* | ``details``: The Action Provider-specific state, particularly the completion
    state, of the Action are returned in the ``details`` field. In the completion
    states, the ``details`` can be considered the "result" or the "return value" of
    the Action. It is the successful return value for a ``SUCCEEDED`` status,  and
    it is the error result for the ``FAILED`` status. The exact content in
    ``details`` is always specific to the Action Provider, so must be documented by
    the Action Provider to describe its interpretation to clients.

* | ``monitor_by`` and ``manage_by``: Same as in the Action Request.

* | ``start_time`` and ``completion_time``: Represent the time the Action was
    first received by the  ``/run`` operation and the time the Action Provider
    determined that the Action reached a completed state (``SUCCEEDED`` or
    ``FAILED``) respectively. Action Providers are not required to continuously
    monitor the progress of Actions, so the ``completion_time`` noted may be
    different than the executed Action's actual completion time.  These values
    **may** be the same in the case of a synchronous operation, but
    ``completion_time`` must never be before ``start_time``.

* | ``release_after``: As stated above, Action state is automatically removed
    from the Action Provider after some time interval once it reaches a completion
    state. The ``release_after`` is a time duration, in seconds, which states how
    long after completion the Action will automatically be released. A typical value
    would be 30-days, but Action Providers may define their own policy which is to
    be exposed in the Action Status.

In addition to the ``/run`` method described above, the Action Status is the
"universal" return value from operations on an Action. We describe the
operations on Actions next. Each uses the ``action_id`` as part of the URL path
much like other RESTful resources do with their ids, and none of them require
any input body. 

* | ``GET /<action_id>/status``: This is a read-only operation for retrieving
    the most recent state of the Action. It is commonly used to poll an Action's
    state while awaiting it entering a completion state. Use of this API call
    requires that the user authenticate with a principal value which is in the
    ``monitor_by`` list established when the Action was started.

* | ``POST /<action_id>/cancel``: Cancellation provides an advisory or hint to
    the Action Provider that the user does not want the Action to continue
    execution. The Action Provider is not required to ensure immediate completion or
    that the cancel operation truly causes the Action to terminate in any manner
    other than it would have without the cancel request. Thus, the Action Status
    returned from the cancel operation may contain a non-completion state. If the
    Action is already in a completed state, the Action Provider may treat the
    request much as a ``/status`` request to simply return the current status. Use
    of this API call requires that the user authenticates with a principal value
    which is in the ``manage_by`` list established when the Action was started. 

* | ``POST /<action_id>/release``: As described in the section on life-cycle,
    the very last step of the life-cycle is for the Action state to be removed from
    the Action Provider. A user can specify that it has retrieved the final state or
    is no longer interested in the state using the ``/release`` operation which
    returns the final state. If the Action is not already in a completion state,
    ``/release`` will return an error as this operation does not attempt to stop
    execution (that is what ``/cancel`` does). The Action Status document returned
    from ``/release`` will be the last record of the Action present at the Action
    Provider. After the call to ``/release`` the ``action_id`` is no longer valid,
    and use in any other calls will return an error, most likely an HTTP status 404
    indicating the Action was not found.

Detailed Execution History: logging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some Actions, particularly those that are long running, may have associated with
them a list or log of activities or sub-events which occurred during the
Action's life. This detailed log is typically larger, more complex, or more
fine-grain than the snapshot of the status returned by the ``/status`` method.
Not all Action Providers or Actions are suitable for logging, so support is
considered optional and will be advertised by the Action Provider in its
description (see below). The request to retrieve the log takes the form ``GET
/<action_id>/log?<filters,pagination>``. The filters and pagination query
parameters are used to limit (e.g. based on start time) which log records to
retrieve and the pagination parameter is used to scroll through a long set of
log records across multiple requests. Each record in the log contains the
following properties:

* | ``time``: A timestamp representing the time this log record occurred.

* | ``code``: A short Action Provider-specific description of the type of the log record.

* | ``description``: A textual description of the purpose, cause, or information
    on the log record.

* | ``details`` (optional): An object providing additional and structured Action
    Provider-specific representation of the log record.


Action Provider Introspection (``GET /``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Automate platform is intended to help users both find and make use of the
variety of Action Providers which may be available on the network. The primary
means of accomplishing this assistance is by making Action Providers, the
services which implement the Action Provider Interface, self-describing via an
*Introspection* interface. Accessing the introspection method is performed
simply via a ``GET /``. That is, the HTTP ``GET`` method on the Base URL. The
returned JSON document contains the following fields:

* | ``api_version``: A version string defining the version of the Action
    Provider Interface supported by the Action Provider. The version described in
    this document and currently the only version available will have value
    ``"1.0"``.

* | ``title``, ``subtitle``, ``description``, ``keywords``: Each of these
    provide human-readable text which helps a user discover the purpose of the
    Action Provider.

* | ``visible_to`` and ``runnable_by``: Access to the action provider is limited
    by and published through these properties. Each contains a list of principal
    values in URN format. ``visible_to`` controls who can retrieve the information
    via introspection (this operation) and may contain the string ``"public"``
    indicating that all users, even those who present no credentials, may access the
    information. The ``runnable_by`` property enumerates who can use the ``/run``
    method to start an Action at this provider. It allows the string
    ``"all_authenticated_users"`` indicating that any user who presents valid
    credentials via a Bearer token may start an Action at the provider.

* | ``synchronous`` and ``log_supported``: These are boolean values which simply
    describe capabilities and modes for the Action Provider. If ``synchronous`` is
    true, a user calling ``/run`` can assume that the returned status will always be
    in a completed (``SUCCEEDED`` or ``FAILED``) state and there will never be a
    need to poll using the ``/status`` method (use of ``/release`` is still
    permitted and encouraged to remove the status from the Action Provider). As
    indicated in the discussion of the ``/log`` method, support for it is optional,
    and the ``log_supported`` flag provides an indication to users whether they can
    make use of ``/log`` for fine grained monitoring of an Action.

* | ``input_schema``: The ``input_schema`` value provides a complete schema
    description for the ``body`` property of the Action Request understood by this
    Action Provider. The schema is provided in `JSON Schema
    <https://json-schema.org/>`_ format.


Setting Up an Action Provider in Globus Auth
============================================

The Action Provider Interface makes use of and is bound closely with
authentication via the `Globus Auth <https://globus.org/>`_ system. To
authenticate RESTful requests using Globus Auth, a service must register as a
"resource server". This is a multi-step process involving use of both the Globus
Auth developer portal, and the Globus Auth API for configuring various access
control states. To help with this process, we provide a step-by-step guide to
using Globus Auth for this purpose:

1. Register a new App on `<https://developers.globus.org>`_ using a browser.
After insuring that you are logged in to the developer portal in a browser at
this URL, perform the following steps:

   - Click Add another project

     - | Provide a name, contact email and select which of your own Globus Auth
        linked identities are permitted to administer the project. You will be
        required to login with this identity in future interactions with the Globus
        Developer Portal to manipulate the resource server.

   - Find your new, empty project, and select Add drop down and "new app"

     - | Provide a name for the specific app within the project. This will be a
        common name displayed to  users when they make use of the Action Provider.

     - | When creating a resource server, the other fields on the app creation
        page are not used.

       - | "Redirects" is not used, but a value must be provided. You can use a
            URL associated with your service or a placeholder value like
            "https://localhost".

       - | "Scopes" are not relevant and make no difference, so this field
            should be left blank. The "Privacy Policy" and "Terms and Conditions"
            may be displayed to users making use of your action provider, but they
            are not required.

   - | Make note of the "Client Id" in the expanded description of your app. This
        value will be used elsewhere in the creation of the service and is often
        referenced as ``client_id``.

   - | In the section "Client Secrets" click "Create a new secret"

     - | Provide a name which is meaningful to you. It will not be displayed to
            other users. 

     - | Make note of the generated secret. Like the ``client_id`` this will be
            used later in development. Be sure **not to lose it** as it can only be
            displayed once. However, new client secrets can be created and old ones
            deleted at any time should the need for a replacement secret arise.

     - | Set the client_id and client_secret on your command line to follow
            along with the rest of this guide.

            .. code-block:: BASH    

                export CLIENT_ID=<client_id>
                export CLIENT_SECRET=<client_secret>

2. Use the Globus Auth REST API to introspect your Action Provider Resource
Server and create required Scopes.

     .. note:: 
        In the examples below, we will use the command line tool ``curl`` to
        perform the HTTP operations as it is very widely available. We also use
        the command line tool ``jq`` to format the ``curl`` command's json
        responses. However, other tools and clients exist for interacting with
        REST and HTTP services, so you may need to translate the ``curl`` and
        ``jq`` commands to your preferred tools.

   - | Introspect the Globus Auth client to see the same settings you setup in
        the developer portal. Notice we exported the ``<client_id>`` and
        ``<client_secret>`` values generated during your registration on the Globus
        Developer Portal into environment variables. 
    
        .. code-block:: BASH

            curl -s --user $CLIENT_ID:$CLIENT_SECRET \ 
                https://auth.globus.org/v2/api/clients/$CLIENT_ID | jq
        
   - | A successful return from this command is a JSON representation of the
        Globus Auth client similar to:

        .. code-block:: JSON

            {
            "client": {
                "scopes": [],
                "redirect_uris": [
                "https://localhost"
                ],
                "name": "My Action Provider",
                "links": {
                "privacy_policy": null,
                "terms_and_conditions": null
                },
                "grant_types": [
                "authorization_code",
                "client_credentials",
                "refresh_token",
                "urn:globus:auth:grant_type:dependent_token"
                ],
                "fqdns": [],
                "visibility": "private",
                "project": "a47b9014-9250-4e21-9de5-b4aac81d464b",
                "required_idp": null,
                "preselect_idp": null,
                "id": "8e98ba5a-21a9-4bef-ab6a-0fcdbed36405",
                "public_client": false,
                "parent_client": null
              }
            }


   - | Of note is the field ``scopes``. ``scopes`` are created to identify
        operations on the Action Provider. Typically, an Action Provide defines just
        one scope and it is provided to users in the Action Provider's introspection
        (``GET /``) information in the field ``globus_auth_scope``.

     - Creating a Scope:  
        - | Creation of a scope is required as the scope will be used in
            authenticating REST calls on the Action Provider.
        
        - | Start by creating a "scope definition" JSON document in the
                following format replacing the ``name``, ``description`` and optionally
                the ``scope_suffix``

            .. code-block:: JSON

                {
                    "scope": {
                        "name": "Action Provider Operations",
                        "description": "All Operations on My Action Provider",
                        "scope_suffix": "action_all",
                        "dependent_scopes": [{
                            "optional": false,
                            "requires_refresh_token": true,
                            "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f"
                         }],             
                        "advertised": true,
                        "allow_refresh_tokens": true
                    }
                }


        - | The ``name`` and ``description`` fields are purely informative and
            will be presented to other users who use the Globus Auth API to lookup
            the scope. The ``scope_suffix`` will be placed at the end of the
            generated "scope string" which is a URL identifier for the scope. It
            provides the context for the operations this scope covers among all
            operations your service provides. For Action Providers, we commonly use
            ``action_all`` to indicate all operations defined by the Action Provider
            API, but any string is acceptable.

        - | ``dependent_scopes`` define scopes of other Globus Auth resource
            servers that your Action Provider will invoke to perform its work. For
            example, if your Action Provider uses Globus Transfer to first move some
            data to compute upon, the scope for the Globus Transfer service would be
            placed in the ``dependent_scopes`` list. In the most common case, as
            shown in the example, the scope for the `Globus Groups API
            <https://docs.globus.org/api/groups/>`_ (with UUID
            ``73320ffe-4cb4-4b25-a0a3-83d53d59ce4f``) should be listed. This allows
            your Action Provider to determine what groups a user calling the
            provider belongs to and can therefore enforce policies, such as
            ``runnable_by`` or ``monitor_by`` based on group membership. If this
            scope is not listed as a dependent scope, the Action Provider Tools
            library will not be able to, and will therefore not attempt to, retrieve
            a user's groups and so no policies based on Groups may be used. We
            encourage you to consult the `Globus Auth Documentation
            <https://docs.globus.org/api/auth/>`__ for more information on creation
            and management of Scopes for more advanced scenarios such as other
            dependent Globus Auth based services such as Globus Transfer.
            
            Note: Scopes supplied in the dependent_scopes array must be
            identified by their UUID. The snippet below demonstrates how to
            lookup a scope's UUID based on its uniquely idenfitfying FQDN

                .. code-block:: BASH
                
                    # Target FQDN is https://auth.globus.org/scopes/actions.globus.org/transfer/transfer
                    export SCOPE_STRING=https://auth.globus.org/scopes/actions.globus.org/transfer/transfer
                    curl -s -u "$CLIENT_ID:$CLIENT_SECRET" \
                        "https://auth.globus.org/v2/api/scopes?scope_strings=$SCOPE_STRING" | jq ".scopes[0].id"

        
        - | The ``advertised`` property indicates whether the scope will be
            visible to all users who do scope look ups on Globus Auth. You may
            select either ``true`` or ``false`` for this depending on your own
            policy. ``allow_refresh_tokens`` should generally be set to ``true``,
            indicating that a client of the Action Provider who has authenticated
            the user via Globus Auth is allowed to refresh that authentication
            without further interactions from the user. Especially in the case where
            an Action may be long running and is monitored by an automated system
            like Globus Flows, it is important that token refresh is permitted.

        - | With the scope creation JSON document complete, use the following
            REST interaction to create the scope in Globus Auth via the ``curl``
            command

            .. code-block:: BASH

                curl -s --user "$CLIENT_ID:$CLIENT_SECRET" -H \
                    'Content-Type: application/json' \
                    -XPOST https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes \
                    -d '<Insert Scope creation document from above>' | jq

        - | This should return the definition of the new scope matching the
            values provided in your scope creation document. As an example:

            .. code-block:: JSON

                {
                    "scopes": [
                        {
                            "dependent_scopes": [{
                                "optional": false,
                                "requires_refresh_token": true,
                                "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f"
                             }],
                            "description": "<your description>",
                            "allows_refresh_token": true,
                            "client": "<client_id>",
                            "advertised": true,
                            "scope_string": "https://auth.globus.org/scopes/<client_id>/action_all",
                            "id": "<A UUID for this scope>",
                            "name": "<your scope name>"
                        }
                    ]
                }

        - | The returned ``scope_string``, which always takes the form of a URL,
            will be the value exposed to users who wish to authenticate with Globus
            Auth to use your Action Provider. It will be part of the Action Provider
            description document, returned on the Action Provider Introspection
            operation (``GET /``) with the key ``globus_auth_scope``.

        - | Note that the returned value is an *array* of scopes. That is, more
            than one scope definition may be generated from the single scope
            creation request. This happens in the uncommon case where an FQDN has
            been registered for your ``client_id`` (refer to the `Globus Auth
            Documentation <https://docs.globus.org/api/auth/>`_ for information on
            FQDN registration if you desire it, though it is not recommended). In
            this case, a similar scope definition will also be generated, but the
            ``scope_string`` will contain the FQDN value(s). The ``scope_string``
            values may be used interchangeably both by users requesting
            authentication to the Action Provider and in the ``globus_auth_scope``
            value of the Action Provider Description. 

        - | Check that the created scope(s) are correctly associated with the
            Action Provider:

            .. code-block:: BASH

                curl -s --user $CLIENT_ID:$CLIENT_SECRET \
                    https://auth.globus.org/v2/api/clients/$CLIENT_ID | jq

3. Once your app and its scope(s) have been created and verified, remove your
credentials from your command line environment.  Be sure to take note of the
client ID and its associated client secret for use other places in the toolkit.

            .. code-block:: BASH

                unset CLIENT_ID CLIENT_SECRET
                
Using the Toolkit
==================

This toolkit provides the following components:

1. Authentication helpers that make it easier to validate Globus Auth tokens and
determine if a given request should be authorized

2. An `OpenAPI v3 specification <http://spec.openapis.org/oas/v3.0.2>`_ and
associated helpers that can be used to validate incoming requests and verify
the responses your Action Provider generates. This document also defines the
interface which must be supported by your REST API to have it function as an
Action Provider.

3. Simple bindings for the document types "Action Request" and "Action Status"
to Python Dataclass representations and a helper JsonEncoder for serializing and
deserializing these structures to/from JSON.

4. Helper methods for binding the REST API calls defined by the Action Interface
to a Flask application. These helpers will perform the Authentication and
Validation steps (as provided by components 1 and 2) and communicate with an
Action Provider implementation using the structures defined in 3. For those
users building an Action Provider using Flask, this provides a simplified method
of getting the REST API implemented and removing common requirements so the
focus can be on the logic of the Action provided.


Installation
------------

Installation is via PyPi using, for example:

.. code-block:: BASH

    pip install globus-action-provider-tools


Authentication
---------------

The authentication helpers can be used in your action provider as follows:

.. code-block:: python

    from globus_action_provider_tools.authentication import TokenChecker
    
    # You will need to register a client and scope(s) in Globus Auth
    # Then initialize a TokenChecker instance for your provider:
    checker = TokenChecker(
        client_id='YOUR_CLIENT_ID',
        client_secret='YOUR_CLIENT_SECRET',
        expected_scopes=['https://auth.globus.org/scopes/YOUR_SCOPES_HERE'],
    )


When a request comes in, use your TokenChecker to validate the access token from
the HTTP Authorization header.

.. code-block:: python

    access_token = request.headers['Authorization'].replace('Bearer ', '')
    auth_state = checker.check_token(access_token)


The AuthState has several properties and methods that will make it easier for
you to decide whether or not to allow a request to proceed:

.. code-block:: python

    # This user's Globus identities:
    auth_state.identities
    # frozenset({'urn:globus:auth:identity:9d437146-f150-42c2-be88-9d625d9e7cf9',
    #           'urn:globus:auth:identity:c38f015b-8ad9-4004-9160-754b309b5b33',
    #           'urn:globus:auth:identity:ffb5652b-d418-4849-9b57-556656706970'})
    
    # Groups this user is a member of:
    auth_state.groups
    # frozenset({'urn:globus:groups:id:606dbaa9-3d57-44b8-a33e-422a9de0c712',
    #           'urn:globus:groups:id:d2ff42bc-c708-460f-9e9b-b535c3776bdd'})

.. note::
    The ``groups`` property will only have values if the Groups API scope
    is defined as a dependent scope as described in the previous section.

You'll notice that both groups and identities are represented as strings that
unambiguously signal what type of entity they represent. This makes it easy to
merge the two sets without conflict, for situations where you'd like to work
with a single set containing all authentications:


.. code-block:: python

    all_principals = auth_state.identities.union(auth_state.groups)


The AuthState object also offers a helper method, ``check_authorization()`` that
is designed to help you test whether a request should be authorized:

.. code-block:: python

    resource_allows = ['urn:globus:auth:identity:c38f015b-8ad9-4004-9160-754b309b5b33']
    auth_state.check_authorization(resource_allows)
    # True


This method also accepts two special string values, ``'public'`` and
``'all_authenticated_users'``, together with keyword arguments that enable their use:

.. code-block:: python

    resource_allows = ['public']
    auth_state.check_authorization(resource_allows, allow_public=True)
    # True

    resource_allows = ['all_authenticated_users']
    auth_state.check_authorization(resource_allows, allow_all_authenticated_users=True)
    # True


Caching
^^^^^^^

To avoid excessively taxing Globus Auth, the ``AuthState`` will, by default,
cache identities and group memberships for 30 seconds.

The cache is initialized when you first instantiate your ``TokenChecker()``.
You should only need to create one TokenChecker instance for your application,
and then you can re-use it to check each new token. In the event that you do
need more than one TokenChecker, be aware that all TokenChecker instances in an
app share the same underlying cache. 

It is possible to customize a TokenChecker by supplying a custom configuration
which gets passed on to the dogpile cache backend.  Each new instance of a
TokenChecker with a custom configuration will drop the cache and recreate it
with the desired settings.  Since all TokenCheckers share the same underlying
cache, subsequent attempts to configure the cache will overwrite the previous
cache's settings and therefore only the last applied configuration will persist.

.. code-block:: python

    from globus_action_provider_tools.authentication import TokenChecker

    # Create TokenChecker with default settings
    my_token_checker = TokenChecker(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        expected_scopes=EXPECTED_SCOPES,
    )

    # Creating a TokenChecker with a custom config will drop the previous cache and
    # create it with the new settings. Both TokenCheckers will use this new cache
    new_token_checker = TokenChecker(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            expected_scopes=config["expected_scopes"],
            cache_config={
                "backend": "dogpile.cache.pylibmc",
                "timeout": "60",
                "url": ["127.0.0.1"],
            },
        )

Validation
----------

There is an OpenAPI v3 specification for the Action Provider API available as
described above. From this specification, we derive schemas that can be used to
test incoming and outgoing messages. These schemas may be used to validate input
documents and output documents within the service as follows.

.. code-block:: python

    from globus_action_provider_tools.validation import (
        request_validator,
        response_validator,  
        ValidationRequest,
    )
    
    # Validating a request
    request = ValidationRequest(provider_doc_type='ActionRequest', 
        request_data={"input_data":""})
    result = request_validator.validate(request)
    
    # Or a response:
    response = ValidationRequest(provider_doc_type='ActionStatus', 
        request_data={"output_data":""})
    result = response_validator.validate(response)
    
    # get list of errors
    errors = result.errors
    
    # or get a single string summarizing all errors
    err = result.error_msg


The request and response validation functions both take a ``ValidationRequest``
structure which has the name of the document type to be validated against and
the data to be validated. At present, the document types supported are
``ActionRequest`` and ``ActionStatus`` documents as defined above.

.. note:: 
    There are additional validation helpers available for applications written
    using the Flask framework. Those are described below in the section
    describing the entire set of Flask helpers.

Data Types
----------

The toolkit provides some simple bindings for the document types defined by the
Action Provider Interface to type-annotated Python3 `Dataclasses
<https://docs.python.org/3/library/dataclasses.html>`_. This can provide a
convenient way to manipulate these document types within an Action
Provider implementation. We also provider an ActionProviderJsonEncoder which can
be used with the built-in Python json package to properly encode these data
types into JSON.

.. code-block:: python

    from globus_action_provider_tools.data_types import (
        ActionProviderJsonEncoder,
        ActionStatus,
        ActionStatusValue,
    )

    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=caller_id,
        monitor_by=request.monitor_by,
        manage_by=request.manage_by,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after=60 * 60 * 24 * 30,  # 30-days in seconds
        display_status=ActionStatusValue.SUCCEEDED.name,
        details=result_details,
    )
    json_string = json.dumps(action_status, cls=ActionProviderJsonEncoder)


Flask Helper
------------

As Action Providers are HTTP-servers, a common approach to building them is to
use the `Flask <https://palletsprojects.com/p/flask/>`_ framework. To aid in
developing Flask-based Action Providers, helper methods are provided which
encapsulate much of the other functionality in the framework: authentication,
validation and serialization for easy use in a Flask-based application. Rather
than defining each of the Action Provider Interface routes in the Flask
application, helpers are provided which declare the necessary routes to Flask,
perform the serialization, validation and authentication on the request, and
pass only those requests which have satisfied these conditions on to a
user-defined implementation of the routes.

To use the helpers, you must define functions corresponding to the various
methods of the Action Provider interface (``run``, ``status``, ``release``,
``cancel``), and must provide the Action Provider introspection information in
an instance of the ``ActionProviderDescription`` dataclass defined in
the tookit's ``data_types`` package. The application must also provide a Flask
``blueprint`` object to which the toolkit can attach the new routes. It is
recommended that the ``blueprint`` be created with a ``url_prefix`` so that the
Action Provider Interface routes are rooted at a distinct root path in the
application's URL namespace.

A brief example of setting up the flask helper is provided immediately below. A
more complete example showing implementation of all the required functions is
provided in the *examples/watchasay* directory. It is appropriate to use the
example as a starting point for any new Action Providers which are developed.

.. code-block:: python
                
    from globus_action_provider_tools.data_types import (
        ActionProviderDescription,
        ActionRequest,
        ActionStatus,
        ActionStatusValue,
    )
    from globus_action_provider_tools.flask import (
        ActionStatusReturn,
        add_action_routes_to_blueprint,
    )

    action_blueprint = Blueprint("action", __name__, url_prefix="/action")
    
    provider_description = ActionProviderDescription(
        globus_auth_scope="<scope created in Globus Auth>",
        title="My Action Provider",
        admin_contact="support@example.com",
        synchronous=True,
        input_schema={}, # JSON Schema representation of the input on the request
        log_supported=False
    )

    add_action_routes_to_blueprint(
        action_blueprint,
        CLIENT_ID,
        CLIENT_SECRET,
        CLIENT_NAME,
        provider_description,
        action_run,
        action_status,
        action_cancel,
        action_release,
    )


In this example, the values ``CLIENT_ID``, ``CLIENT_SECRET`` and ``CLIENT_NAME``
are as defined in Globus Auth as described above (where ``CLIENT_NAME`` is
almost always passed as ``None`` except in the uncommon, legacy case where a
particular name has been associated with a Globus Auth client). The values
``action_run``, ``action_status``, ``action_cancel`` and ``action_release`` are
all **functions** which will be called by the framework when the corresponding
HTTP requests are called. Where appropriate, these functions are implemented in
terms of the toolkit's data types so the need for JSON serialization and
deserialization is greatly reduced from the application code. The framework will
also provide validation of input ``ActionRequest`` data to the ``/run`` method
prior to invoking the ``action_run`` function. As long as the return value from
the various functions is of type ``ActionStatus``, the framework will also
insure that the returned JSON data conforms to the Action Provider Interface.
The **watchasay** example in the ``examples/`` directory demonstrates how these
functions can be implemented.