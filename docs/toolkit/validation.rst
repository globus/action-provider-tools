Validation
==========

Validation using Pydantic
-------------------------

We provide Pydantic_ models which automatically handle the validation of input
and output documents upon creation. Both the ``ActionRequest`` and
``ActionStatus`` classes from the data_types module will produce standardized,
informative errors if instantiated with incorrect information. If these objects
are created correctly when receiving requests and returning results, the
ActionProvider complies with the ``run/`` endpoint specification.

.. code-block:: python

    from pydantic import ValidationError

    from globus_action_provider_tools.data_types import (
        ActionRequest,
        ActionStatus,
    )

    # This will fail since ActionRequest objects minimally require a request_id
    # and body
    try:
        action_request = ActionRequest()
    except ValidationError as ve:
        print(ve.errors())
        # prints: [{'loc': ('request_id',), 'msg': 'field required', 'type': 'value_error.missing'}, {'loc': ('body',), 'msg': 'field required', 'type': 'value_error.missing'}]

    # This will fail since the ActionStatus document requires a creator_id in
    # the form of a Globus ARN
    try:
        action_status = ActionStatus(creator_id="ME", details={},
        status="ACTIVE")
    except ValidationError as ve:
        print(ve.errors())
        # prints: [{'loc': ('creator_id',), 'msg': 'string does not match regex "^urn:globus:(auth:identity|groups:id):([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})$"', 'type': 'value_error.str.regex', 'ctx': {'pattern': '^urn:globus:(auth:identity|groups:id):([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})$'}}]

    # This will succeed and contain fields that default to valid values
    action_request = ActionRequest(request_id=1, body={})
    assert action_request.monitor_by == []

    # Display the ActionRequest JSONSchema
    print(ActionRequest.schema())

.. note::
    The pydantic validation only happens on instantiation. This means that
    accessing and modifying fields after instantiation is possible. There
    are no way to prevent a field from getting set to an incorrect value.

Custom Validation
-----------------

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

.. _Pydantic: https://pydantic-docs.helpmanual.io/
