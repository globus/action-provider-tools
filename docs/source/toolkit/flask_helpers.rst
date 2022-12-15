Flask Helpers
=============
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
