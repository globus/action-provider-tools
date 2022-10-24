#########
watchasay
#########

This is a sample Flask application implementing the simple "echo" Unix command
line utility as an ActionProvider. This example uses the Flask API helpers in
globus_action_provider_tools. Rather than defining each of the
Action Provider Interface routes in the Flask application, the helpers declare
the necessary routes to Flask, perform the serialization, validation and
authentication on the request, and pass only those requests which have satisfied
these conditions on to a user-defined implementation of the routes.

To run a *watchasay* Action, provide a "input_string" parameter indicating the
text to have "echoed" back. Since this ActionProvider is synchronous, each
Action has its status set to "SUCCEEDED" immediately. Note that this Action
Provider is configured to run at the */skeleton* endpoint.

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

        cd examples/watchasay
        pip install -r requirements.txt
        python app/provider.py

Testing the Action Provider
===========================
We provide example tests to validate that your Action Provider is working and
enable some form of continuous integration. To run the example test suite, once
again activate the project's virtualenvironment and run the following:

    .. code-block:: BASH

        cd examples/watchasay
        pytest

Within these tests, we provide examples of how to use a patch that is useful for
testing your Action Provider without using a valid CLIENT_ID, CLIENT_SECRET or
request Tokens. Only use this patch during testing.

Actually using the Action Provider
==================================
You'll notice that the only endpoint we can reach without a valid token is the
introspect endpoint (*/skeleton*). Issuing the below command will report the
expected request schema and the required scope for using the Provider:

    .. code-block:: BASH

        curl http://localhost:5000/skeleton/

Why? It's because the watchasay Provider has been set to be publicly visible.
Setting the introspection endpoint to be publicly visible is useful way of
providing documentation on how to interact with the ActionProvider.
All other operations on the Action Provider will require a valid token:

    .. code-block:: BASH

        curl --request POST \
            --url http://localhost:5000/skeleton/run \
            --header 'authorization: Bearer token' \
            --data '{"request_id": "some-id","body": {"input_string": "hey"}}'


But how to get the token? The recommended route to retrieve a token is to use
the globus-automate-client CLI tool. Conveniently, the globus-automate-client
CLI tool removes the need to create curl requests and the need to manually
format Action request bodies. See the doc on downloading the CLI tool. Once
downloaded, issue a command simliar to to the one below.  The first time you
run the command, you will need to follow a flow to request the necessary grants
for your Action Provider's scopes.  Later attempts to use the
globus-automate-client tool will use locally cached tokens and transparently
refresh expired tokens.

    .. code-block:: BASH

        globus-automate action-run \
            --action-url http://localhost:5000/skeleton/run \
            --action-scope $YOUR_PROVIDERS_SCOPE \
            --body '{"input_string":"hi"}'

Run the CLI tool with the *--help* option for more information.
