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
            "73320ffe-4cb4-4b25-a0a3-83d53d59ce4f",
            optional=False,
            requires_refresh_token=False,
        )
        print(
            client.create_scope(
                client_id=CLIENT_ID,
                name="Action Provider 'all'",
                description="Access to my action provider",
                scope_suffix="action_all",
                dependent_scopes=[groups_scope_spec],
                advertised=True,
            )
        )
    else:
        raise NotImplementedError


if __name__ == "__main__":
    main()
