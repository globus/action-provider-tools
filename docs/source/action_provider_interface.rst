Action Provider Interface
=========================

We provide an overview of the *Action Provider Interface* as a guide for use
when implementing an *Action Provider*.

.. raw:: html
    :file: cli/example_action_run.html

The Action Provider Interface is a RESTful model for starting, monitoring,
canceling and removing state associated with the invocation of an Action.
Following the REST resource life-cycle pattern, each Action invocation returns
an identifier representing the invocation (an *Action Instance*). This
identifier is used to monitor the progress of the Action Instance via further
REST calls until its completion, or it may be used to request cancellation of
the action instance.

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
and how it can transition between the states. The states are defined as follows:

*  ``ACTIVE``: The Action is executing and is making progress toward completion.

* | ``INACTIVE``: The Action is paused in its execution and is not making
    progress toward completion. Out-of-band (i.e. not via the Action Provider
    Interface) measures may be required to allow the Action to proceed.

* | ``SUCCEEDED``: The Action reached a completion state which was considered
    "normal" or not due to failure or other unrecoverable error.

* | ``FAILED``: The Action is in a completion state which is "not normal" such as
    due to an error condition which is not considered recoverable in any manner.

* | ``RELEASED``: The Action Provider has removed the record of the existence of
    the Action. Further attempts to interact with the Action will be errors as if
    the Action had never existed. All resources associated with the Action may have
    been deleted or removed. This is not a true state in the sense that the state
    can be observed, but ultimately all Actions will be released and unavailable for
    further operations. Any subsequent references to the Action, e.g. via the API
    methods described below, will behave as if the Action never existed.

Upon initial creation of an Action (see operations below), the Action may be in
any of the first four states. If it is in an ``ACTIVE`` or ``INACTIVE`` state,
the Action is considered "asynchronous" and further queries to get the state of
the Action may return updated information. If the Action is in the
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

Action Provider Document Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
    the following sections, we present the key concepts, but do not enumerate
    every option or field on the documents. Refer to the toolkit components,
    including the OpenAPI format specification (as described in the toolkit
    section), for a complete definition.

Starting an Action: The Action Request Document
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Starting an Action is performed by making a REST ``POST`` request to the path
``/run`` containing an Action Request document. The request document contains
the following fields:

* | ``request_id``: A client-generated identifier for this request. A user may
    re-invoke the ``/run`` method with the same ``request_id`` any number of times,
    but the Action must only be initiated once. In this way, the user may re-issue
    the request in case it cannot be determined if a request was successfully
    initiated for example due to network failure.

* | ``manage_by`` and ``monitor_by``: Each of these is a **list** of principal
    values in `URN format <https://docs.globus.org/api/search/#principal_urns>`_,
    and they allow the user invoking the Action to delegate some capability over the
    Action to other principals. ``manage_by`` defines the principals who are allowed
    to attempt to change the execution of the Action (see operations ``/cancel`` and
    ``/release`` below) while it is running. ``monitor_by`` defines principals which
    are allowed to see the state of the Action before its state has been destroyed
    in a release operation. In both cases, the Globus Auth identity associated with
    the ``/run`` operation is implicitly part of both the ``manage_by`` and
    ``monitor_by`` sets. That is, the invoking user need not include their own
    identity into these lists.

* | ``body``: An Action Provider-specific object which provides the input for
    the Action to be performed. The ``body`` must conform to the input
    specification for the Action Provider being invoked, and thus the client must
    understand the requirements of the Action Provider when providing the value of
    the ``body``. Thus, the Action Provider must provide documentation on the format
    for the ``body`` property.

.. code-block:: JSON
   :caption: Action Request Document for running the Hellow World Action Provider

    {
        "request_id": "0112358132134",
        "monitor_by": [
            "urn:globus:auth:identity:46bd0f56-e24f-11e5-a510-131bef46955c",
            "urn:globus:groups:id:fdb38a24-03c1-11e3-86f7-12313809f035"
        ],
        "body": {
            "echo_string": "Hello there!"
        }
    }

Any request to the ``/run`` method which contains an Action Request which
adheres to the input schema will return an Action Status document as described
in the next section.

Monitoring and Managing an Action: The Action Status Document
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

All information about an Action is contained in the Action Status document which
is returned on almost all operations related to an Action (the exception is the
log operation which is optional and is described briefly below). Notable fields
of the Action Status document include:

* | ``action_id``: The unique identifier for this particular action. The
    ``action_id`` is a string, and it should be treated as an opaque value
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
    *may* be the same in the case of a synchronous operation, but
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
an input body.

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


Action Provider Introspection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

Detailed Execution History: Logging
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some Actions, particularly those that are long running, may have associated with
them a list or log of activities or sub-events which occurred during the
Action's life. This detailed log is typically larger, more complex, or more
fine-grain than the snapshot of the status returned by the ``/status`` method.
Not all Action Providers or Actions are suitable for logging, so support is
considered optional and will be advertised by the Action Provider in its
description (see above). The request to retrieve the log takes the form ``GET
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

Optional Endpoint: Action Enumeration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In some cases, it may be useful for an Action Provider to provide an endpoint
through which Action execution histories can be queried. This is particularly
useful for administrators who are interested in collecting success and failure
information from the Action Provider, or for users who simply want a list of
currently executing Actions that may be waiting for some external action. This
enumeration endpoint supports filters via query parameters to indicate to the
type of ActionStatuses to return.

The supported query parameters are ``roles`` and ``status``, where roles can
be any one or more of ``creator_id``, ``monitor_by``, ``manage_by``.
Using the ``roles`` filter will only retrieve Actions where the requestor's
identity is listed in the selected Action's field. If unset, this parameter
defaults to ``creator_id``.

The ``status`` query can be any one or more of ``active``, ``inactive``,
``failed``, ``succeded``, which corresponds exactly to all possible Action
states.  If multiple statuses are queried for, the set of Actions returned will
each have a status that was in the query set. If unset, this parameter defaults
to ``active``. This field is case insensitive.

When both of these filters are used together, the resulting set of Actions will
contain the result of applying a logical AND between the results of the two
filters. That is, the Actions in the returned set will contain actions with a
status listed in the ``status`` filter and the returned actions will also list
the requestor as an identity in the queried ``roles``. The query takes the form
of ``GET /actions?roles=role1,role2,role3&status=status_1,status2``.

.. note::

    Please note that as this is an optional endpoint, not all Action Providers
    implement this functionality.


Next Steps
^^^^^^^^^^
Now that you're familiar with the Action Provider Interface and capabilities,
you're one step closer to writing your own Action Provider. The next step is to
create a :doc:`Globus Auth Resource Server<setting_up_auth>`.
