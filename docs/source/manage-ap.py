import argparse
import sys

import globus_sdk

# CUSTOMIZE THESE VARIABLES
# ------------------------------------------------------------------------

# Fill in the CLIENT_* variables when creating an App and a Client Secret.
CLIENT_ID = "YOUR_ID_HERE"
CLIENT_SECRET = "YOUR_SECRET_HERE"

# Modify the SCOPE_* variables BEFORE running the `create-scope` command.
SCOPE_NAME = "Action Provider 'all'"
SCOPE_DESCRIPTION = "Access to my action provider"
SCOPE_SUFFIX = "action_all"
SCOPE_DEPENDENCIES = [
    # Most action providers must be able to look up a caller's groups
    # for authorization purposes, so by default this script
    # adds the Globus Groups "View Groups and Memberships" scope
    # as a dependent scope.
    globus_sdk.DependentScopeSpec(
        "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f",
        optional=False,
        requires_refresh_token=False,
    ),
]

# Fill in the scope ID variable AFTER running the `create-scope` command.
AP_SCOPE_ID = "YOUR_SCOPE_ID_HERE"

# ------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser("manage-ap")
    parser.add_argument(
        "action",
        choices=("show-self", "create-scope", "show-scope", "update-scope"),
    )
    args = parser.parse_args()

    if args.action == "show-self":
        show_self()
    elif args.action == "create-scope":
        create_scope()
    elif args.action == "show-scope":
        show_scope()
    elif args.action == "update-scope":
        update_scope()
    else:
        print(f"The action '{args.action}' is not recognized.", file=sys.stderr)
        raise SystemExit(1)


def show_self() -> None:
    client = _get_client()
    print(client.get_identities(ids=CLIENT_ID))


def create_scope() -> None:
    client = _get_client()
    print(
        client.create_scope(
            client_id=CLIENT_ID,
            name=SCOPE_NAME,
            description=SCOPE_DESCRIPTION,
            scope_suffix=SCOPE_SUFFIX,
            dependent_scopes=SCOPE_DEPENDENCIES,
            advertised=True,
        )
    )


def show_scope() -> None:
    client = _get_client()
    try:
        print(client.get_scope(AP_SCOPE_ID))
    except globus_sdk.AuthAPIError:
        print("The scope doesn't appear to exist.")
        print("(Have you run the 'create-scope' command?)")
        raise SystemExit(1)


def update_scope() -> None:
    client = _get_client()
    try:
        print(
            client.update_scope(
                AP_SCOPE_ID,
                name=SCOPE_NAME,
                description=SCOPE_DESCRIPTION,
                scope_suffix=SCOPE_SUFFIX,
                dependent_scopes=SCOPE_DEPENDENCIES,
                advertised=True,
            )
        )
    except globus_sdk.AuthAPIError:
        print("The scope doesn't appear to exist.")
        print("(Have you run the 'create-scope' command?)")
        raise SystemExit(1)


def _get_client() -> globus_sdk.AuthClient:
    app = globus_sdk.ClientApp(
        "manage-ap", client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )

    client = globus_sdk.AuthClient(app=app)
    client.add_app_scope(globus_sdk.AuthClient.scopes.manage_projects)
    return client


if __name__ == "__main__":
    main()
