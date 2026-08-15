Data Types
==========

The toolkit provides some simple bindings for the document types defined by the
Action Provider Interface to type-annotated Pydantic_ models. These classes
provide a convenient way to manipulate these document types within an Action
Provider implementation. We also provider an ActionProviderJsonEncoder which
can be used with the built-in Python json package to properly encode these data
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

.. _Pydantic: https://pydantic-docs.helpmanual.io/
