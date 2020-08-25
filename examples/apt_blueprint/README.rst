#############
APT Blueprint
#############

This is a sample Flask application implemented using the Flask Decorators in the
Action Provider Toolkit. The Toolkit provides an ActionProviderBlueprint with five
decorators which are used to decorate functions that will be run when the Action
Provider is invoked. Each decorator corresponds to one of the Action Provider
Interface endpoints. The decorators available are: 

- action_run
- action_status
- action_cancel
- action_release
- action_log


Using the Toolkit
=================
The *ActionProviderBlueprint* is exactly like a Flask Blueprint, except it has
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
*ActionProviderDescription* and use it when creating the
*ActionProviderBlueprint*. 

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

Once the ActionProviderBlueprint has been created, use its decorators to
register functions which implement your ActionProvider's logic.

    .. code-block:: python    
        
        @aptb.action_run
        def my_action_run(action_request: ActionRequest, auth: AuthState):
            pass

        @aptb.action_status
        def my_action_status(action_id: str, auth: AuthState, *args):
            pass

        @aptb.action_cancel
        def my_action_cancel(action_id: str, auth: AuthState, *args):
            pass

        @aptb.action_release
        def my_action_release(action_id: str, auth: AuthState, *args):
            pass

        @aptb.action_log
        def my_action_log(action_id: str, auth: AuthState, *args):
            pass


Later, register the *ActionProviderBlueprint* to your Flask app exactly as your
would register any other Flask Blueprint and run your ActionProvider:

    .. code-block:: python

        from flask import Flask

        app = Flask(__name__)
        app.config.from_object("config")
        app.register_blueprint(aptb)
        app.run()

  .. note::

    One important difference between the *ActionProviderBlueprint* and a regular
    Flask Blueprint is that internally, the *ActionProviderBlueprint* will
    create *TokenChecker* instance upon registration with a Flask application.
    This *TokenChecker* is what handles all authentication and authorization to
    the *ActionProvider*. As such, the Flask application must be configured to
    contain a valid Globus Auth **client ID** and **client secret**. An
    *ActionProviderBlueprint* will attempt to pull these credentials from
    application is is registered to's configuration. First, the Blueprint checks
    to see if there is configuration of the form BLUEPRINT_NAME_CLIENT_ID
    BLUEPRINT_NAME_CLIENT_SECRET. If that configuration is not found, the
    Blueprint will look for a generic CLIENT_ID CLIENT_SECRET configuration to
    use.

    As an example, if we created the following *ActionProviderBlueprint*:
    
    .. code-block:: python    
        
        aptb = ActionProviderBlueprint(
            name="apt",
            import_name=__name__,
            url_prefix="/apt",
            provider_description=description,
        )

    Once the *aptb* Blueprint gets registered with a Flask app, it will attempt
    to find APT_CLIENT_ID and APT_CLIENT_SECRET variables in the
    Flask application's configuration. Failing to find those, it will use the
    Flask application's CLIENT_ID and CLIENT_SECRET variables.


Presteps
========
To run this example Action Provider, you will need to generate your own
CLIENT_ID, CLIENT_SECRET, and SCOPE.  It may be useful to follow the directions
for generating each of these located at README.rst. Once you have those three
values, place them into the example Action Provider's config.py.

Starting the Action Provider
============================
We recommend creating a virtualenvironment to install project dependencies and
run the Action Provider. Once the virtualenvironment has been created and
activated, run the following:

    .. code-block:: BASH    

        cd examples/flask/apt_blueprint
        pip install -r requirements.txt
        python app.py
