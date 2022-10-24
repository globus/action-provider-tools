####################
whattimeisitrightnow
####################

From the makers of Philbert: Another exciting promotional tie-in for whattimeisitrightnow.com
#############################################################################################

This is a sample Flask application implementing the ActionProvider interface. It
accepts requests with a "utc_offset" parameter indicating which timezone to
return the current UTC time as. To demonstrate some degree of complexity, the
application randomly assigns each request an *estimated_completion_time* so that
an action's results will not be available until the *estimated_completion_time*.
To do this, we store and make use of "private" data fields which are never
displayed to any requestor. Additionally, some percentage of requests to the
ActionProvider fail to demonstrate how to report errors back to the requestors.

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

        cd examples/whattimeisitrightnow
        pip install -r requirements.txt
        python app/app.py

Testing the Action Provider
===========================
We provide example tests to validate that your Action Provider is working and
enable some form of continuous integration. To run the example test suite, once
again activate the project's virtualenvironment and run the following:

    .. code-block:: BASH

        cd examples/whattimeisitrightnow
        pytest

Within these tests, we provide examples of how to use a patch that is useful for
testing your Action Provider without using a valid CLIENT_ID, CLIENT_SECRET or
request Tokens. Only use this patch during testing.

Actually using the Action Provider
==================================
You'll notice that just because its running doesn't mean we can actually use the
Action Provider. In particular, once the whattimeisitrightnow Action Provider is
run, this will fail:

    .. code-block:: BASH

        curl http://localhost:5000/

Why? It's because the whattimeisitrightnow Provider has been set to be visible
to only authenticated users (see the ActionProviderDescription initialization
values).  Therefore, requests need proper HTTP authorization headers (i.e.
a token needs to be provided):

    .. code-block:: BASH

        curl --request GET \
            --url http://localhost:5000/ \
            --header 'authorization: Bearer token'

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

        globus-automate action-provider-introspect \
            --action-url http://localhost:5000/ \
            --action-scope $YOUR_PROVIDERS_SCOPE

The globus-automate-client CLI tool can also make requests to endpoints besides
the introspection endpoint, for example:

    .. code-block:: BASH

        globus-automate action-run \
            --action-url http://localhost:5000/ \
            --action-scope $YOUR_PROVIDERS_SCOPE \
            --body '{"utc_offset": 1}'

Run the CLI tool with the *--help* option for more information.
