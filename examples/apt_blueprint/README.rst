Overview
^^^^^^^^
This is a sample Flask application implemented using the Flask Decorators in the
Action Provider Toolkit. The Toolkit provides an `ActionProviderBlueprint` with five
decorators which are used to decorate functions that will be run when the Action
Provider is invoked. Each decorator corresponds to one of the Action Provider
Interface endpoints. The decorators available are:

- `action_run`
- `action_status`
- `action_cancel`
- `action_release`
- `action_log`


Using this Tool
^^^^^^^^^^^^^^^
The `ActionProviderBlueprint` is exactly like a Flask `Blueprint`, except it has
been customized to implement the *Action Provider Interface* and ties together
much of the tooling available in the rest of the Toolkit to provide a
streamlined development experience. The ActionProviderBlueprint will:

- Validate that incoming requests to your ActionProvider adhere to the
  ActionRequest schema
- Validate that incoming requests to your ActionProvider adhere to your
  ActionProvider's defined input-schema
- Automatically create routes implementing the Action Provider Interface
- Enforce that only expected users can acccess your ActionProvider's
  *introspection* and *run* endpoints.
- Return valid views to callers.

All the ActionProvider developer needs to do is create an
`ActionProviderDescription` and use it when creating the
`ActionProviderBlueprint`:

.. code-block:: python

    from globus_action_provider_tools.flask.apt_blueprint import (
        ActionProviderBlueprint)
    from globus_action_provider_tools.data_types import (
        ActionProviderDescription)

    description = ActionProviderDescription(...)
    aptb = ActionProviderBlueprint(
        name="apt",
        import_name=__name__,
        url_prefix="/apt",
        provider_description=description,
    )

.. note::
    The ``ActionProviderBlueprint`` is really just a Flask ``Blueprint`` in
    disguise. As such, any keyword arguments you pass to it get passed onto the
    underlying ``Blueprint`` constructor, giving you the familiar interface and
    capabilities of the Flask ecosystem.

Once the ActionProviderBlueprint has been created, use its decorators to
register functions which implement your ActionProvider's logic:

.. code-block:: python

    @aptb.action_run
    def my_action_run(action_request: ActionRequest, auth: AuthState):
        pass

    @aptb.action_status
    def my_action_status(action_id: str, auth: AuthState):
        pass

    @aptb.action_cancel
    def my_action_cancel(action_id: str, auth: AuthState):
        pass

    @aptb.action_release
    def my_action_release(action_id: str, auth: AuthState):
        pass

    @aptb.action_log
    def my_action_log(action_id: str, auth: AuthState):
        pass

.. note::
    It's required that your decorated functions accept two positional arguments
    with the correct types. For the `action_run` function, the argument types
    need to be an ``ActionRequest`` and an ``AuthState``. The rest of the
    functions will have argument types of ``str`` and ``AuthState``. Within
    your function, you will have access to the requestors Globus Authentication
    information.


The toolkit provides a convenient way of authorizing access to an Action when a
request to view or modify the Action's execution gets made. You can import them
via:

.. code-block:: python

    from globus_action_provider_tools.authorization import (
        authorize_action_access_or_404, authorize_action_management_or_404)

To use these, obtain an `ActionStatus` object from your ActionProvider's storage
backend and use the provided `AuthState` argument:

.. code-block:: python

    @aptb.action_status
    def my_action_status(action_id: str, auth: AuthState):
        # Lookup ActionStatus via action_id
        action_status = ...
        authorize_action_access_or_404(action_status, auth)
        ...

    @aptb.action_cancel
    def my_action_cancel(action_id: str, auth: AuthState):
        # Lookup ActionStatus via action_id
        action_status = ...
        authorize_action_management_or_404(action_status, auth)
        ...

.. note::
    You generally only want to use `authorize_action_access_or_404` in the
    `action_status` and `action_log` endpoint functions. `action_cancel` and
    `action_release` should use `authorize_action_management_or_404`.

Later, register the `ActionProviderBlueprint` to a Flask app exactly as you
would register any other Flask Blueprint and run your ActionProvider:

    .. code-block:: python

        from flask import Flask

        app = Flask(__name__)
        app.config.from_object("config")
        app.register_blueprint(aptb)
        app.run()

.. note::
    One important difference between the `ActionProviderBlueprint` and a regular
    Flask Blueprint is that internally, the `ActionProviderBlueprint` will
    create a `TokenChecker` instance upon registration with a Flask application.
    This `TokenChecker` is what handles all authentication and authorization to
    the *ActionProvider*. As such, the Flask application must be configured to
    contain a valid Globus Auth **client ID** and **client secret**. An
    `ActionProviderBlueprint` will attempt to pull these credentials from
    application it is registered to's configuration. First, the Blueprint checks
    to see if there are configuration keys of the form "BLUEPRINT_NAME_CLIENT_ID"
    and "BLUEPRINT_NAME_CLIENT_SECRET". If those configuration keys are not found,
    the Blueprint will look for the keys "CLIENT_ID" and "CLIENT_SECRET" in the
    app's configuration. If these configuration values cannot be found, the Action
    Provider will not be able to authenticate requests against Globus Auth.

    As an example, if we created the following `ActionProviderBlueprint`:

    .. code-block:: python

        aptb = ActionProviderBlueprint(
            name="apt",
            import_name=__name__,
            url_prefix="/apt",
            provider_description=description,
        )

    Once `aptb` gets registered with a Flask app, it will attempt to find the
    "APT_CLIENT_ID" and "APT_CLIENT_SECRET" keys in the Flask application's
    configuration. Failing to find those, it will search for and use the Flask
    application's "CLIENT_ID" and "CLIENT_SECRET" values.

Example Configuration
=====================

To run this example Action Provider, you need to generate your own
CLIENT_ID, CLIENT_SECRET, and SCOPE.  It may be useful to follow the directions
for generating each of these located at :ref:`globus_auth_setup`. Once you have
those three values, place the CLIENT_ID and CLIENT_SECRET into the example
Action Provider's `config.py` and update the `ActionProviderDescription`'s
`globus_auth_scope` value in `blueprint.py`.


We recommend creating a virtualenvironment to install project dependencies and
run the Action Provider. Once the virtualenvironment has been created and
activated, run the following:

    .. code-block:: BASH

        cd examples/apt_blueprint
        pip install -r requirements.txt
        python app.py
