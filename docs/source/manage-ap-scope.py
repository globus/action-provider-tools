import argparse
import sys

import globus_sdk

# CUSTOMIZE THESE VARIABLES
# ------------------------------------------------------------------------

# Fill in the CLIENT_* variables when creating an App and a Client Secret.
CLIENT_ID = "YOUR_ID_HERE"
CLIENT_SECRET = "YOUR_SECRET_HERE"

# Modify the SCOPE_* variables BEFORE running the `create` command.
SCOPE_NAME = "<NAME>"  # Example: "Action Provider 'all'"
SCOPE_DESCRIPTION = "<DESCRIPTION>"  # Example: "Allow my AP to do X-Y-Z"
SCOPE_SUFFIX = "<your_scope_suffix_here>"  # Example: "action_all"
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

# Fill in the scope ID variable AFTER running the `create` command.
AP_SCOPE_ID = "YOUR_SCOPE_ID_HERE"

# ------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser("manage-ap-scope")
    parser.add_argument(
        "action",
        choices=("show-client", "create", "show", "update"),
    )
    args = parser.parse_args()

    if args.action == "show-client":
        show_client()
    elif args.action == "create":
        create()
    elif args.action == "show":
        show()
    elif args.action == "update":
        update()
    else:
        print(f"The action '{args.action}' is not recognized.", file=sys.stderr)
        raise SystemExit(1)


def show_client() -> None:
    client = _get_client()
    print(client.get_identities(ids=CLIENT_ID))


def create() -> None:
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


def show() -> None:
    client = _get_client()
    try:
        print(client.get_scope(AP_SCOPE_ID))
    except globus_sdk.AuthAPIError:
        print("The scope doesn't appear to exist.")
        print("(Have you run the 'create' command?)")
        raise SystemExit(1)


def update() -> None:
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
        print("(Have you run the 'create' command?)")
        raise SystemExit(1)


def _get_client() -> globus_sdk.AuthClient:
    app = globus_sdk.ClientApp(
        "manage-ap-scope", client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )

    client = globus_sdk.AuthClient(app=app)
    client.add_app_scope(globus_sdk.AuthClient.scopes.manage_projects)
    return client


if __name__ == "__main__":
    main()
