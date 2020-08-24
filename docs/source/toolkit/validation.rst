Validation
==========

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
