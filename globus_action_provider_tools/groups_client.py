import os
from typing import AbstractSet, Any, Dict, List, Optional, Set

from globus_sdk.authorizers import GlobusAuthorizer
from globus_sdk.base import BaseClient
from globus_sdk.exc import GlobusAPIError, GlobusError
from globus_sdk.response import GlobusHTTPResponse

GROUPS_API_ENVIRONMENTS: Dict[str, str] = {
    "default": "https://groups.api.globus.org",
    "production": "https://groups.api.globus.org",
    "preview": "",
    "sandbox": "https://groups.api.sandbox.globuscs.info",
    "test": "https://groups.api.test.globuscs.info",
    "integration": "https://groups.api.integration.globuscs.info",
    "staging": "https://groups.api.staging.globuscs.info",
}


class GroupsClient(BaseClient):
    def __init__(self, authorizer: GlobusAuthorizer, *args, **kwargs):
        """
        The Globus SDK only pulls the service URL from its config if it isn't
        provided on initialization. So here we'll figure it out for ourselves
        and set it appropriately.
        """
        environment = os.environ.get("GLOBUS_SDK_ENVIRONMENT", "default").lower()
        super().__init__(
            "groups",
            *args,
            base_url=GROUPS_API_ENVIRONMENTS[environment],
            authorizer=authorizer,
            **kwargs,
        )

    def list_groups(
        self, roles: AbstractSet[str] = frozenset(("member", "admin", "manager"))
    ) -> List[Dict[str, Any]]:
        resp: GlobusHTTPResponse = self.get("/v2/groups/my_groups")
        data = resp.data
        groups: List[Dict[str, Any]] = []
        for group in data:
            for membership in group.get("my_memberships"):
                role = membership.get("role")
                if role in roles:
                    groups.append(group)
                    break
        return groups
