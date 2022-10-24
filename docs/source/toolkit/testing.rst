Testing
=======

An Action Provider is closely integrated with Globus Auth (see
:ref:`globus_auth_setup`). This integration makes it easy to validate incoming
requests and ensures that the requestor is authorized to execute actions against
an Action Provider. However, the integration can make it difficult to run tests
against an Action Provider to validate that its endpoints behave correctly.
During a CI/CD pipeline, it may be a requirement to start your Action Provider
without a valid Client ID or Secret.

The toolkit provides various tools to enable testing and validation in the
:code:`globus_action_provider_tools.testing` module.


Fixtures
^^^^^^^^

The toolkit provides various `pytest fixtures
<https://docs.pytest.org/en/stable/fixture.html>`_  that greatly reduce the need
to manually mock and patch interactions with Globus Auth. If an Action Provider
is created using any of the Flask helpers provided in the
:code:`globus_action_provider_tools.flask` module, we provide a fixture to
easily mock authentication out of your Action Provider. Each of the Flask
helpers internally creates a *TokenChecker* which does two things: it validates
that the Action Provider is correctly configured with a valid Globus Auth Client
ID and Secret, and it validates that incoming requests contain a valid token.
These fixtures abstract both aspects of the internal *TokenChecker* so that you
can focus on testing your Action Provider's behavior and logic.


Action Provider Blueprint
-------------------------

If your Action Provider is built using the *ActionProviderBlueprint* Flask
helper, use the :code:`apt_blueprint_noauth` fixture in
:code:`globus_action_provider_tools.testing.fixtures`:

.. code-block:: python

    from globus_action_provider_tools.testing.fixtures import (
        apt_blueprint_noauth
    )

Once imported, it can be used just as any other pytest fixture. We recommend
passing it as a parameter to another fixture which ultimately creates the app
and returns a resource for use in tests. Provide the fixture your
*ActionProviderBlueprint* instance under test. This will update your instance
with stubbed out authentication. The example below shows how to create a
:code:`client` fixture which can be used to make unauthenticated HTTP requests
against the Action Provider:

.. code-block:: python

    from myapp import action_provider_blueprint

    @pytest.fixture(scope="module")
    def client(apt_blueprint_noauth):
        apt_blueprint_noauth(action_provider_blueprint)
        app = create_app()
        yield app.test_client()

Once composed like this, you can use the :code:`client` fixture in your tests to
receive and use a Flask *test_client* to make unauthenticated requests against
your Action Provider:

.. code-block:: python

    def test_introspection_endpoint(client):
        response = client.get("/")
        assert response.status_code == 200


Flask API Helpers
-----------------

If your Action Provider is built using the
:code:`add_action_routes_to_blueprint` Flask helper, use the
:code:`flask_helpers_noauth` fixture in
:code:`globus_action_provider_tools.testing.fixtures*`:

.. code-block:: python

    from globus_action_provider_tools.testing.fixtures import (
        flask_helpers_noauth
    )

Once imported, simply pass the :code:`flask_helpers_noauth` fixture as a
parameter to another fixture which creates the app and returns a resource for
use in tests. Unlike the :code:`apt_blueprint_noauth` fixture, the
:code:`flask_helpers_noauth` fixture does not need to be explicitly executed -
simply passing it as a parameter is sufficient to temporarily stub out the
Provider's authentication. An example of how to create a :code:`client` fixture
which can be used to make unauthenticated HTTP requests against the Action
Provider is shown below:

.. code-block:: python

    @pytest.fixture(scope="module")
    def client(flask_helpers_noauth):
        app = create_app()
        app.config["TESTING"] = True
        yield app.test_client()

Once composed like this, you can use the :code:`client` fixture in your tests to
receive and use a Flask *test_client* to make requests against your Action
Provider:

.. code-block:: python

    def test_introspection_endpoint(client):
        response = client.get("/")
        assert response.status_code == 200

.. note::

    The :code:`flask_helpers_noauth` fixture will patch the TokenChecker in a
    global scope during testing, meaning that any other Action Providers that
    are themselves built using the Flask API Helpers will also have their
    TokenChecker's patched. This may lead to unintended issues if testing
    multiple Action Providers in the same pytest test session. If this is your
    case, we highly recommend isolating your Action Provider tests.


Mocks
^^^^^

The toolkit provides various `mocks
<https://docs.python.org/3/library/unittest.mock.html#the-mock-class>`_ which
can be used individually to stub out your Action Provider's authentication. You
should use these directly if you are writing an Action Provider using a
non-Flask framework or if you've decided not to use the built in Flask helpers.

.. note::

    This toolkit uses these mocks within the
    :code:`globus_action_provider_tools.testing.fixtures` module.


.. _mock-authstate:

Mock AuthState
--------------

An *AuthState* represents a requestor's authentication status and Globus Auth
information. Every request should have its token validated via the
*TokenChecker*'s :code:`check_token` method, which in turns generates an
*AuthState* object.

During testing, it is convenient to not provide valid tokens with every request.
Use the :code:`mock_authstate` mock to generate a stubbed out *AuthState* object
that won't validate requestor properties against Globus Auth. This is most
useful when used in a patch as the return value for the *TokenChecker*'s
:code:`check_token` method:

.. code-block:: python

    import pytest
    from globus_action_provider_tools.testing.mocks import mock_authstate

    @pytest.fixture
    def client(monkeypatch):
        monkeypatch.setattr(
            "globus_action_provider_tools.authentication.TokenChecker.check_token",
            mock_authstate,
        )
        yield app.test_client()

The example above creates a fixture which can be used to create a client that
can make unauthenticated HTTP requests against an Action Provider.


Mock TokenChecker
-----------------

Because the *TokenChecker* is this toolkit's authentication workhorse, it's
possible to entirely replace the the *TokenChecker* with a mock object. Doing so
will allow your Action Provider to start up without validating its Client ID or
Secret and will also allow unauthenticated requests to be made against it. This
mock provides a simple way of completely removing your app's authentication
during testing.


.. code-block:: python

    from unittest import mock

    import pytest
    from globus_action_provider_tools.testing.mocks import mock_tokenchecker

    @pytest.fixture
    def client():
        with mock.patch(
            "my_package.my_app.get_tokenchecker",
            return_value=mock_tokenchecker(),
        ):
            app = create_app()
            app.config["TESTING"] = True
            yield app.test_client()


.. note::

    This example will only work if there's a function or method that is used to
    create the TokenChecker instance. It demonstrates how you can patch a
    function or a method to return the Mock TokenChecker. Internally, the Mock
    TokenChecker will generate the :ref:`mock-authstate` objects described
    above.
