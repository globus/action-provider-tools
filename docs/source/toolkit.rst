Action Provider Tools
=====================
This toolkit provides the following components:

1. :doc:`Authentication helpers<toolkit/authentication>` that make it easier to
validate Globus Auth tokens and determine if a given request should be authorized.

2. Pydantic_ and `OpenAPI v3 specification`_ based :doc:`validation
helpers<toolkit/validation>` that can be used to validate
incoming requests and verify the responses your Action Provider generates. This
document also defines the interface which must be supported by your REST API to
have it function as an Action Provider.

3. :doc:`Simple bindings<toolkit/data_types>` for the document types ``Action
Request`` and ``Action Status`` to Python object representations and a helper
JsonEncoder for serializing and deserializing these structures to/from JSON.

4. :doc:`Flask helper methods <toolkit/flask_helpers>` for binding the REST API
calls defined by the Action Interface to a Flask application. These helpers will
perform the Authentication and Validation steps (as provided by components 1 and
2) and communicate with an Action Provider implementation using the structures
defined in 3. For those users building an Action Provider using Flask, this
provides a simplified method of getting the REST API implemented and removing
common requirements so the focus can be on the logic of the Action provided.

5. :doc:`Caching guide <toolkit/caching>` for tweaking the performance of Action
Providers with relation to Globus Auth.

6. :doc:`Testing tools <toolkit/testing>` provides various resources for
stubbing Authentication out of an Action Provider and providing a simple way of
validating an Action Provider's behavior.

.. toctree::
   :maxdepth: 1
   :hidden:

   toolkit/authentication
   toolkit/caching
   toolkit/data_types
   toolkit/flask_helpers
   toolkit/validation
   toolkit/testing


.. _Pydantic: https://pydantic-docs.helpmanual.io/

.. _OpenAPI v3 specification: http://spec.openapis.org/oas/v3.0.2
