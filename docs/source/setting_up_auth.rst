.. _globus_auth_setup:

Set Up an Action Provider in Globus Auth
########################################

In the Globus ecosystem, services use
`Globus Auth <https://docs.globus.org/api/auth/>`_
to handle user authentication. In order for an **action provider** to function, it
needs to be configured as a service in Globus Auth.

This guide doc will walk you through the setup process.

As part of this process, you'll use a small Python script
to help manage your action provider's Globus Auth scope.


Prerequisites
=============

Step 0: Install the Globus SDK
------------------------------

We recommend using virtualenvs for Python applications.
Use these commands to create and activate a virtualenv in a development directory:

.. tab-set::

    .. tab-item:: Unix/macOS

       .. code-block:: shell

          python -m venv venv
          source venv/bin/activate

    .. tab-item:: Windows

       .. code-block:: shell

          py -m venv venv
          venv\Scripts\activate.bat

Finally, install the SDK:

.. code-block:: bash

    pip install globus-sdk


Steps
=====

Step 1: Download ``manage-ap-scope.py``
---------------------------------------

To assist with scope creation and management, download :download:`manage-ap-scope.py`.

This is a template script; you'll need to fill in several variables in the file
as you complete steps in this guide.


Step 2: Create an Auth Client
-----------------------------

In Globus Auth, applications are represented as **clients**.
Your **client** registration will be your way of managing settings for your
**action provider**.

When you create your **client**, you will also be prompted to create or use a **project**.
A **project** is a grouping of **clients** which lets you assign administrators.

#.  Go to `the Globus Web App Developers page`_.
#.  Click "Advanced registration".
#.  Select "none of the above - create a new project" and click "Continue".

    Fill in the required project information and click "Continue".

    You may have to re-authorize through your identity provider
    due to security policies associated with project management.
    If this happens, follow the on-screen prompts.
    You'll be redirected to the App Registration page.

#.  Fill in the "App Name" field.

    If applicable, enter URLs for your privacy policy and terms of service.

    Do not modify any other settings on the page.

    Then, click "Register App".

Stay on the resulting application page!
We will continue from here in the next step.


Step 3: Create and Record a Client Secret and the Client ID
-----------------------------------------------------------

Your **action provider** will need credentials to communicate with Globus Auth.
These will be used to validate credentials sent by users
and resolve them to user IDs and Groups.

From the application page, you will create and save a new **client secret**.

..  note::

    In this guide, we will store the Client UUID and Secret in the ``manage-ap-scope.py`` script.
    You can store this data in another way at your discretion.

#.  Copy the Client UUID and save it in ``manage-ap-scope.py``
    in the variable named ``CLIENT_ID``.
    For example:

    ..  code-block:: python

        CLIENT_ID = "11111111-2222-3333-4444-555555555555"

#.  Click "Add Client Secret".
#.  Type a name for the Client Secret and click "Generate Secret".
#.  Save the secret in ``manage-ap-scope.py`` in the variable ``CLIENT_SECRET``.
    For example:

    ..  code-block:: python

        CLIENT_SECRET = "aBcDeFgH/iJkL+mNoP="

    ..  warning::

        The Client Secret will never be shown a second time.
        Make sure you copy the secret *exactly*.
        Use the copy button to be sure.


Step 4: Verify Your Credentials
-------------------------------

In this step, we'll run ``manage-ap-scope.py``
to verify that the Client ID and Secret were saved correctly.

Run ``python manage-ap-scope.py show-client``.
Your output should look similar to the following:

..  code-block:: json

    {
      "identities": [
        {
          "organization": null,
          "email": null,
          "name": "your-app-name"
          "identity_provider": "3a74877b-e2a3-44b1-8958-ede1031b1827",
          "id": "11111111-2222-3333-4444-555555555555",
          "identity_type": null,
          "status": "used",
          "username": "11111111-2222-3333-4444-555555555555@clients.auth.globus.org",
        }
      ]
    }


As long as there are no errors and you get a JSON response with an
``identities`` array, it means the credentials are working.


Step 5: Create the Action Provider Scope
----------------------------------------

Globus Auth scopes allow services to control the level of access
that applications grant one another.

For a full explanation, see the `clients, scopes, and consents documentation`_.

To function properly, an **action provider** must define exactly one scope.
Additional scopes can be defined as needed,
but there is only one per **action provider**.

#.  Modify the ``SCOPE_*`` variables in ``manage-ap-scope.py``.
#.  Run the ``manage-ap-scope.py`` script, using the ``create-scope`` subcommand:

..  code-block:: bash

    python manage-ap-scope.py create

You should see output similar to the following:

..  code-block:: json

    {
      "scopes": [
        {
          "dependent_scopes": [
            {
              "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f",
              "optional": false,
              "requires_refresh_token": false
            }
          ],
          "advertised": true,
          "allows_refresh_token": true,
          "required_domains": [],
          "client": "11111111-2222-3333-4444-555555555555",
          "id": "66666666-7777-8888-9999-000000000000",
          "description": "Access to my action provider",
          "name": "Action Provider 'all'",
          "scope_string": "https://auth.globus.org/scopes/11111111-2222-3333-4444-555555555555/action_all"
        }
      ]
    }

Congratulations, you have a scope for your **action provider**!

Copy the full scope's ``id`` to the ``manage-ap-scope.py`` script.
For example:

..  code-block:: python

    AP_SCOPE_ID = "66666666-7777-8888-9999-000000000000"

When communicating with other services
or configuring your **action provider** with ``globus_action_provider_tools`` you will always use
the full scope string.

..  note::

    **The Globus Groups scope**

    In order to register inter-service dependencies,
    scopes need to declare how they relate to other scopes,
    which may potentially be owned by other applications.

    **Action Providers** almost always need to view a user's groups and memberships.
    This scope is built into the ``manage-ap-scope.py`` script.
    You can confirm the Globus Groups "View My Groups and Memberships" scope ID
    using the Globus CLI:

    ..  code-block:: bash

         globus api auth GET /v2/api/scopes \
            -Q 'scope_strings=urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships' \
            --jq 'scopes[0].id'

Step 6: Verify the scope
------------------------

After creating the scope and saving its ID in ``manage-ap-scope.py``,
run one more verification step:

..  code-block:: shell

    python manage-ap-scope.py show

You should see JSON output identical to the output of the ``create`` subcommand.


Conclusion
==========

In this guide, you've:

*   Registered a new Globus Auth project
*   Registered a new Globus Auth application that represents your Action Provider
*   Created a Client Secret for the Action Provider to use
*   Created a scope so that users can use the Action Provider in a flow


Next Steps
==========

If you want to update the details of your scope,
you can modify the ``SCOPE_*`` variables in ``manage-ap-scope.py``
and then run ``python manage-ap-scope.py update``.

For information on installing Action Provider Tools,
see the :doc:`installation docs <installation>`.

For information on the library's components,
see the :doc:`toolkit documentation <toolkit>`.

To see a few sample **action provider** implementations,
head over to the :doc:`examples page <examples>`.


..  Links
..  -----
..
..  _the Globus Web App Developers page: https://app.globus.org/settings/developers
..  _clients, scopes, and consents documentation: https://docs.globus.org/guides/overviews/clients-scopes-and-consents/
