.. _globus_auth_setup:

Set Up an Action Provider in Globus Auth
========================================

The Action Provider Interface makes use of and is bound closely with
authentication via the `Globus Auth
<https://docs.globus.org/api/auth/specification/>`_ system. To
authenticate RESTful requests using Globus Auth, a service must register as a
"resource server". This is a multi-step process involving use of both the Globus
Auth developer portal and the Globus Auth API for configuring various access
control states. To help with this process, we provide a step-by-step guide to
using Globus Auth for this purpose

.. note::
    In the examples below, we will use the command line tool ``curl`` to
    perform the HTTP operations as it is widely available. We also use the
    command line tool ``jq`` to format the ``curl`` command's json responses.
    However, other tools and clients exist for interacting with REST and HTTP
    services, so you may need to translate the ``curl`` and ``jq`` commands to
    your preferred tools.

Step 1: Register a new App
^^^^^^^^^^^^^^^^^^^^^^^^^^

Register a new App on `<https://developers.globus.org>`_ using a browser.
Once logged in, perform the following steps

- Select "Add another project"

  - | Provide a name, contact email and select which of your own Globus Auth
        linked identities are permitted to administer the project. You will be
        required to login with this identity in future interactions with the Globus
        Developer Portal to manipulate the resource server.

- After filling in your new Project's details, select "Create Project"

- | Find your new, empty project, and select the "Add" drop down and then click
    "Add new app"

  - | Provide a name for the specific app within the project. This will be a
      common name displayed to users when they make use of the Action Provider.
      "Redirects" is not used, but a value must be provided. You can use a
      URL associated with your service or a placeholder value like "https://localhost".

  - | When creating a resource server, the other fields on the app creation page
      are not used. On this menu, "Scopes" is not relevant and make no
      difference, so this field should be left blank. The "Privacy Policy" and
      "Terms and Conditions" may be displayed to users making use of your action
      provider, but they are not required.

- Select "Create app"

- You will be redirected to the "Apps and Services" page. Scroll to your
  Project, then to the newly created App. Make note of the "Client ID" in the
  expanded description of your app. This value will be used elsewhere in the
  creation of the service and is often referenced as ``client_id``.

- In the section "Client Secrets" click "Generate New Client Secret"

  - | Provide a Description which is meaningful to you. It will not be
      displayed to other users.

- Click "Generate Secret".

  - | Make note of the generated secret. Like the ``client_id`` this will be
      used later in development. Be sure **not to lose it** as it can only be
      displayed once. However, new client secrets can be created and old ones
      deleted at any time should the need for a replacement secret arise.

- | Set the client_id and client_secret on your command line to follow
    along with the rest of this guide.

    .. code-block:: BASH

        export CLIENT_ID=<client_id>
        export CLIENT_SECRET=<client_secret>


Step 2: Use the Globus Auth API to introspect your Action Provider Resource Server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- | Introspect your Globus Auth client to see the same settings you setup in
    the developer portal. Notice we exported the ``<client_id>`` and
    ``<client_secret>`` values generated during your registration on the Globus
    Developer Portal into environment variables.

    .. code-block:: BASH

        curl -s --user $CLIENT_ID:$CLIENT_SECRET \
            https://auth.globus.org/v2/api/clients/$CLIENT_ID | jq

- | A successful return from this command is a JSON representation of the
    Globus Auth client similar to:

    .. code-block:: JSON

        {
            "client": {
                "scopes": [],
                "redirect_uris": [
                    "https://localhost"
                ],
                "name": "My Action Provider",
                "links": {
                    "privacy_policy": null,
                    "terms_and_conditions": null
                },
                "grant_types": [
                    "authorization_code",
                    "client_credentials",
                    "refresh_token",
                    "urn:globus:auth:grant_type:dependent_token"
                ],
                "fqdns": [],
                "visibility": "private",
                "project": "a47b9014-9250-4e21-9de5-b4aac81d464b",
                "required_idp": null,
                "preselect_idp": null,
                "id": "8e98ba5a-21a9-4bef-ab6a-0fcdbed36405",
                "public_client": false,
                "parent_client": null
            }
        }

- | Of note is the ``scopes`` field. ``scopes`` are created to identify
    operations on the Action Provider. Typically, an Action Provide defines just
    one scope and it is provided to users in the Action Provider's introspection
    (``GET /``) information in the field ``globus_auth_scope``. In the next
    section, we demonstrate how to create a ``scope``.


Step 3. Create your Action Provider's Scope
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- | Creation of a scope is required as the scope will be used in authenticating
    REST calls on the Action Provider.

- | Start by creating a "scope definition" JSON document in the
    following format replacing the ``name``, ``description`` and optionally
    the ``scope_suffix``.

    .. code-block:: JSON

        {
            "scope": {
                "name": "Action Provider Operations",
                "description": "All Operations on My Action Provider",
                "scope_suffix": "action_all",
                "dependent_scopes": [
                        {
                            "optional": false,
                            "requires_refresh_token": true,
                            "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f"
                        }
                    ],
                "advertised": true,
                "allow_refresh_tokens": true
            }
        }

- | The ``name`` and ``description`` fields are purely
    informative and will be presented to other users who use the Globus Auth API
    to lookup the scope. The ``scope_suffix`` will be placed at the end of the
    generated "scope string" which is a URL identifier for the scope. It
    provides the context for the operations this scope covers among all
    operations your service provides. For Action Providers, we commonly use
    ``action_all`` to indicate all operations defined by the Action Provider
    API, but any string is acceptable.

- | The ``advertised`` property indicates whether the scope will be
    visible to all users who do scope look ups on Globus Auth. You may select
    either ``true`` or ``false`` for this depending on your own policy.
    ``allow_refresh_tokens`` should generally be set to ``true``, indicating
    that a client of the Action Provider who has authenticated the user via
    Globus Auth is a allowed to refresh that authentication without further
    interactions from the user. Especially in the case where an Action may be
    long running and is monitored by an automated system like Globus Flows, it
    is important that token refresh is permitted.

- | ``dependent_scopes`` define scopes of other Globus Auth resource
    servers that your Action Provider will invoke to perform its work. For
    example, if your Action Provider uses Globus Transfer to first move some
    data to compute upon, the scope for the Globus Transfer service would be
    placed in the ``dependent_scopes`` list. In the most common case, as
    shown in the example, the scope for the `Globus Groups API
    <https://docs.globus.org/api/groups/>`_ (with UUID
    ``73320ffe-4cb4-4b25-a0a3-83d53d59ce4f``) should be listed. This allows
    your Action Provider to determine what groups a user calling the
    provider belongs to and can therefore enforce policies, such as
    ``runnable_by`` or ``monitor_by`` based on group membership. If this
    scope is not listed as a dependent scope, the Action Provider Tools
    library will not be able to, and will therefore not attempt to, retrieve
    a user's groups and so no policies based on Groups may be used. We
    encourage you to consult the `Globus Auth Documentation
    <https://docs.globus.org/api/auth/>`_ for more information on creation
    and management of Scopes for more advanced scenarios such as other
    dependent Globus Auth based services such as Globus Transfer.

    .. note::
        Scopes supplied in the dependent_scopes array must be identified by
        their UUID. The snippet below demonstrates how to look up a scope's UUID
        based on its uniquely idenfitfying FQDN

    .. code-block:: BASH

        # Target FQDN is https://auth.globus.org/scopes/actions.globus.org/transfer/transfer
        export SCOPE_STRING=https://auth.globus.org/scopes/actions.globus.org/transfer/transfer
        curl -s -u "$CLIENT_ID:$CLIENT_SECRET" \
            "https://auth.globus.org/v2/api/scopes?scope_strings=$SCOPE_STRING" | jq ".scopes[0].id"


- | With the scope creation JSON document complete, use the following REST
    interaction to create the scope in Globus Auth via the ``curl`` command.

    .. code-block:: BASH

        curl -s --user "$CLIENT_ID:$CLIENT_SECRET" -H \
            'Content-Type: application/json' \
            -XPOST https://auth.globus.org/v2/api/clients/$CLIENT_ID/scopes \
            -d '<Insert Scope creation document from above>' | jq

- | This command should return the definition of the new scope matching the
    values provided in your scope creation document. As an example:

    .. note::
        The returned value is an *array* of scopes. That is, more than one scope
        definition may be generated from the single scope creation request. This
        happens in the uncommon case where an FQDN has been registered for your
        ``client_id`` (refer to the `Globus Auth Documentation
        <https://docs.globus.org/api/auth/>`_ for information on FQDN
        registration if you desire it, though it is not recommended). In this
        case, a similar scope definition will also be generated, but the
        ``scope_string`` will contain the FQDN value(s). The ``scope_string``
        values may be used interchangeably both by users requesting
        authentication to the Action Provider and in the ``globus_auth_scope``
        value of the Action Provider Description.

    .. code-block:: JSON

        {
            "scopes": [
                {
                    "dependent_scopes": [
                            {
                            "optional": false,
                            "requires_refresh_token": true,
                            "scope": "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f"
                            }
                        ],
                    "description": "<your description>",
                    "allows_refresh_token": true,
                    "client": "<client_id>",
                    "advertised": true,
                    "scope_string": "https://auth.globus.org/scopes/<client_id>/action_all",
                    "id": "<A UUID for this scope>",
                    "name": "<your scope name>"
                }
            ]
        }

- | The returned ``scope_string``, which always takes the form of a URL, will be
    the value exposed to users who wish to authenticate with Globus Auth to use
    your Action Provider. It will be part of the Action Provider description
    document, returned on the Action Provider Introspection operation (``GET
    /``) with the key ``globus_auth_scope``.

- | Verify that the created scope(s) are correctly associated with the Action
    Provider:

    .. code-block:: BASH

        curl -s --user $CLIENT_ID:$CLIENT_SECRET \
            https://auth.globus.org/v2/api/clients/$CLIENT_ID | jq

- | Once your app and its scope(s) have been created and verified, remove your
    credentials from your command line environment. Be sure to take note of the
    client ID and its associated client secret for use in other places in the toolkit.

    .. code-block:: BASH

        unset CLIENT_ID CLIENT_SECRET

Next Steps
^^^^^^^^^^
Once you have obtained your own CLIENT_ID and created a CLIENT_SECRET and
SCOPE, you have all the pieces required for creating an Action Provider.

For information on installing the toolkit read the :doc:`installation
page<installation>`.

For information on this toolkit's components, read the :doc:`toolkit
documentation<toolkit>`.

To see a few sample Action Provider implementations head over to the
:doc:`examples page<examples>`.
