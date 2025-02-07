.. _globus_auth_setup:

Set Up an Action Provider in Globus Auth
========================================

In the Globus ecosystem, services use
`Globus Auth <https://docs.globus.org/api/auth/>`_
to handle user authentication. In order for an **action provider** to function, it
needs to be configured as a service in Globus Auth.

This guide doc will walk you through the setup process.

As part of this process, we will build a small Python application to manage your
Globus Auth scopes. Managing your application's resources via code is a best
practice and will make your action provider easier to build and maintain.

Prerequisites
-------------

This guide will use the Globus Python SDK, which requires that you have Python
installed.
If a supported version of Python is not already installed on your system, see
this `Python installation guide \
<https://docs.python-guide.org/starting/installation/>`_.

Steps
-----

Step 1: Install the SDK
'''''''''''''''''''''''

We recommend using virtualenvs for python applications. Create a virtualenv in
a development directory:

.. tab-set::

    .. tab-item:: Unix/macOS

       .. code-block:: shell

          python -m venv venv

    .. tab-item:: Windows

       .. code-block:: shell

          py -m venv venv

Activate the virtualenv:

.. tab-set::

    .. tab-item:: Unix/macOS

       .. code-block:: shell

          source venv/bin/activate

    .. tab-item:: Windows

       .. code-block:: shell

          venv\Scripts\activate.bat

Finally, install the SDK:

.. code-block:: bash

    pip install globus-sdk

Step 2: Create an Auth Client
'''''''''''''''''''''''''''''

In Globus Auth, applications are represented as **client**\s.
Your **client** registration will be your way of managing settings for your
Action Provider.

When you create your **client**, you will also be prompted to create or use a
**project**. A **project** is a grouping of **client**\s which lets you assign
administrators.

1.  Go to `the Developers page <https://app.globus.org/settings/developers>`_.

2.  Select ``Advanced registration``.

3.  Create a new **project** when prompted.

4.  Fill in the **client** fields:

    a.  ``App Name``: The name for your Action Provider.

    b.  ``Redirects``: This field will not be used. Leave it blank.

    c.  Leave the checkboxes at their defaults.

    d.  Optionally enter URLs for your privacy policy and terms of service (if
        applicable).

Stay on the resulting application page!
We will continue from here in the next step.

Step 3: Create and Record a Client Secret and the Client ID
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

Your Action Provider will need credentials to communicate with Globus Auth.
These will be used to validate credentials sent by users and resolve them to
user IDs and Groups.

From the application page for your new client, you will create and save a new
Client Secret. First, prepare a local Python script which will contain the
secret:

1.  Create a new file, ``manage-ap.py``

2.  In your editor, put the following content into ``manage-ap.py``:

    .. code-block:: python

        import globus_sdk

        CLIENT_ID = "..."
        CLIENT_SECRET = "..."

.. note::

    Throughout this guide, we will store the client ID and secret directly in
    the ``manage-ap.py`` script for simplicity. You could move this data to
    another location -- a database, config storage, keychain, environment
    variables -- at your discretion.

    All that matters is that the Python code has access to these values as strings.

Now that we have a storage location prepared, we can create the secret from the
web application:

1.  Select `Add Client Secret`.

2.  Name the secret when prompted, this is a label for your own record keeping.

3.  At this point the secret will be shown **only once**. Save the resulting
    secret in a new python script, filling it in for ``CLIENT_SECRET``.

    .. warning::

        Make sure you copy the secret *exactly*. Use the copy button to be sure.

4.  Record the client ID (``Client UUID``) from the application screen in
    ``CLIENT_ID``.

Step 4: Verify Your Credentials
'''''''''''''''''''''''''''''''

It's always good to double-check things! In this step, we'll verify that the
Client ID and Secret were saved correctly.

1.  Update ``manage-ap.py`` to add the following lines to the end:

    .. code-block:: python

        app = globus_sdk.ClientApp("manage-ap", client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
        client = globus_sdk.AuthClient(app=app)
        print(client.get_identities(ids=CLIENT_ID))

2.  Run ``python manage-ap.py``. Your output should look similar to the
    following:

    .. code-block:: json

        {
          "identities": [
            {
              "organization": null,
              "email": null,
              "name": "your-client-name",
              "identity_provider": "3a74877b-e2a3-44b1-8958-ede1031b1827",
              "id": "your-client-id-goes-here",
              "identity_type": null,
              "status": "used",
              "username": "your-client-id-goes-here@clients.auth.globus.org"
            }
          ]
        }

As long as there are no errors and you get a JSON response with an
``identities`` array, it means the credentials are working.

Step 5: Create the Action Provider Scope
''''''''''''''''''''''''''''''''''''''''

Globus Auth scopes allow services to control the level of access that
applications grant one another. For a full explanation, see the
`official documentation on clients, scopes, and consents
<https://docs.globus.org/guides/overviews/clients-scopes-and-consents/>`_.

For proper function, an Action Provider must define exactly one scope which
will be used by its consumers. Additional scopes can be defined for
applications which serve multiple purposes, but there is only one per Action
Provider.

1.  Update ``manage-ap.py`` to create a scope named ``action_all``. We'll also
    add some use of ``argparse`` in this step so that the script can carry out
    multiple different operations over time:

    .. code-block:: python

        import argparse

        import globus_sdk

        CLIENT_ID = "YOUR_ID_HERE"
        CLIENT_SECRET = "YOUR_SECRET_HERE"

        app = globus_sdk.ClientApp(
            "manage-ap", client_id=CLIENT_ID, client_secret=CLIENT_SECRET
        )

        client = globus_sdk.AuthClient(app=app)
        client.add_app_scope(globus_sdk.AuthClient.scopes.manage_projects)

        parser = argparse.ArgumentParser("manage-ap")
        parser.add_argument("action", choices=("show-self", "create-scope"))


        def main():
            args = parser.parse_args()
            if args.action == "show-self":
                print(client.get_identities(ids=CLIENT_ID))
            elif args.action == "create-scope":
                # we have looked up the scope for Globus Groups for you in this
                # case -- see note below for details
                groups_scope_spec = globus_sdk.DependentScopeSpec(
                    "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f", False, False
                )
                print(
                    client.create_scope(
                        CLIENT_ID,
                        "Action Provider 'all'",
                        "Access to my action provider",
                        "action_all",
                        dependent_scopes=[groups_scope_spec],
                    )
                )
            else:
                raise NotImplementedError


        if __name__ == "__main__":
            main()

2.  Run the script to ``create-scope``:

    .. code-block:: bash

        $ python ./manage-ap.py create-scope
        {
          "scopes": [
            {
              "name": "Action Provider 'all'",
              "allows_refresh_token": true,
              "description": "Access to my action provider",
              "dependent_scopes": [
                {
                  "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f",
                  "optional": false,
                  "requires_refresh_token": false
                }
              ],
              "required_domains": [],
              "id": "THE_SCOPE_ID_HERE",
              "client": "YOUR_CLIENT_ID_HERE",
              "advertised": false,
              "scope_string": "https://auth.globus.org/scopes/YOUR_CLIENT_ID_HERE/action_all"
            }
          ]
        }

At this stage, you have a scope for your Action Provider!

You can think of the scope under two identifiers:

- the full scope string: ``"https://auth.globus.org/scopes/$CLIENT_ID/action_all"``
- the suffix: ``"action_all"``

The full string is globally unique. Even if another application registers
``action_all``, it won't conflict with your application's scope.
The suffix is only unique to your application.

For this reason, when communicating with other services you will always use
the full string.

.. note::

    **The Globus Groups Scope**

    In order to register inter-service dependencies, scopes need to declare how
    they relate to other scopes, potentially from other applications.

    For Action Providers, we will want to be able to view a user's groups using
    the ``"urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships"``
    scope.

    To save you the trouble of finding this scope's ID, we have provided it for
    you above. But you can do it yourself too! Using the Globus CLI, it's easy!
    Just run:

    .. code-block:: bash

         globus api auth GET /v2/api/scopes \
            -Q 'scope_strings=urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships' \
            --jq 'scopes[0].id'

Next Steps
----------

You now have a Client ID and Secret saved in a script, ``manage-ap.py``, and
your application is registered in Globus Auth.

You'll need the Client ID and Secret in order to create an Action Provider
using ``globus_action_provider_tools`` and to run your Action Provider.

``manage-ap.py`` currently only has two capabilities -- self-inspection and creating
a scope -- but you can easily add more. If you want to update your scope
description, you could add an ``"update-scope"`` command and make it call
`client.update_scope
<https://globus-sdk-python.readthedocs.io/en/stable/services/auth.html#globus_sdk.AuthClient.update_scope>`_!

For information on installing Action Provider Tools read the :doc:`installation
page<installation>`.

For information on the library's components, read the :doc:`toolkit
documentation<toolkit>`.

To see a few sample Action Provider implementations head over to the
:doc:`examples page<examples>`.
