Authentication
==============
The authentication helpers can be used in your action provider as follows:

.. code-block:: python

    from globus_action_provider_tools.authentication import TokenChecker

    # You will need to register a client and scope(s) in Globus Auth
    # Then initialize a TokenChecker instance for your provider:
    checker = TokenChecker(
        client_id='YOUR_CLIENT_ID',
        client_secret='YOUR_CLIENT_SECRET',
        expected_scopes=['https://auth.globus.org/scopes/YOUR_SCOPES_HERE'],
    )


When a request comes in, use your TokenChecker to validate the access token from
the HTTP Authorization header.

.. code-block:: python

    access_token = request.headers['Authorization'].replace('Bearer ', '')
    auth_state = checker.check_token(access_token)


The AuthState has several properties and methods that will make it easier for
you to decide whether or not to allow a request to proceed:

.. code-block:: python

    # This user's Globus identities:
    auth_state.identities
    # frozenset({'urn:globus:auth:identity:9d437146-f150-42c2-be88-9d625d9e7cf9',
    #           'urn:globus:auth:identity:c38f015b-8ad9-4004-9160-754b309b5b33',
    #           'urn:globus:auth:identity:ffb5652b-d418-4849-9b57-556656706970'})

    # Groups this user is a member of:
    auth_state.groups
    # frozenset({'urn:globus:groups:id:606dbaa9-3d57-44b8-a33e-422a9de0c712',
    #           'urn:globus:groups:id:d2ff42bc-c708-460f-9e9b-b535c3776bdd'})

.. note::
    The ``groups`` property will only have values if the Groups API scope
    is defined as a dependent scope as described in the previous section.

You'll notice that both groups and identities are represented as strings that
unambiguously signal what type of entity they represent. This makes it easy to
merge the two sets without conflict, for situations where you'd like to work
with a single set containing all authentications:


.. code-block:: python

    all_principals = auth_state.identities.union(auth_state.groups)


The AuthState object also offers a helper method, ``check_authorization()`` that
is designed to help you test whether a request should be authorized:

.. code-block:: python

    resource_allows = ['urn:globus:auth:identity:c38f015b-8ad9-4004-9160-754b309b5b33']
    auth_state.check_authorization(resource_allows)
    # True


This method also accepts two special string values, ``'public'`` and
``'all_authenticated_users'``, together with keyword arguments that enable their use:

.. code-block:: python

    resource_allows = ['public']
    auth_state.check_authorization(resource_allows, allow_public=True)
    # True

    resource_allows = ['all_authenticated_users']
    auth_state.check_authorization(resource_allows, allow_all_authenticated_users=True)
    # True
