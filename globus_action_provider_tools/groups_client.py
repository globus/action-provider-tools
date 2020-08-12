from typing import AbstractSet, Any, Dict, List, Optional, Set

from globus_sdk.authorizers import GlobusAuthorizer
from globus_sdk.base import BaseClient
from globus_sdk.exc import GlobusAPIError, GlobusError
from globus_sdk.response import GlobusHTTPResponse


class GroupsClient(BaseClient):
    BASE_URL = "https://groups.api.globus.org/v2/groups/my_groups"

    def __init__(self, authorizer: GlobusAuthorizer, *args, **kwargs):
        super().__init__(
            "groups_client",
            *args,
            base_url=GroupsClient.BASE_URL,
            authorizer=authorizer,
            **kwargs,
        )

    def list_groups(
        self, roles: AbstractSet[str] = frozenset(("member", "admin", "manager"))
    ) -> List[Dict[str, Any]]:
        resp: GlobusHTTPResponse = self.get("")
        data = resp.data
        groups: List[Dict[str, Any]] = []
        for group in data:
            for membership in group.get("my_memberships"):
                role = membership.get("role")
                if role in roles:
                    groups.append(group)
                    break
        return groups
