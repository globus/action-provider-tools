import logging
from time import time
from typing import FrozenSet, Iterable, List, Optional, Union

from cachetools import LRUCache, TTLCache
from globus_sdk import ConfidentialAppAuthClient
from globus_sdk.auth.token_response import OAuthTokenResponse
from globus_sdk.authorizers import AccessTokenAuthorizer, RefreshTokenAuthorizer
from globus_sdk.exc import GlobusAPIError, GlobusError
from globus_sdk.response import GlobusHTTPResponse

from globus_action_provider_tools.errors import ConfigurationError
from globus_action_provider_tools.groups_client import GROUPS_SCOPE, GroupsClient

log = logging.getLogger(__name__)


def group_principal(id_: str) -> str:
    return f"urn:globus:groups:id:{id_}"


def identity_principal(id_: str) -> str:
    return f"urn:globus:auth:identity:{id_}"


class AuthState(object):
    # Cache for introspection operations, max lifetime: 30 seconds
    introspect_cache: TTLCache = TTLCache(maxsize=100, ttl=30)

    # Cache for dependent tokens, max lifetime: 5 minutes
    dependent_tokens_cache: LRUCache = LRUCache(maxsize=100)

    # Cache for group lookups, max lifetime: 5 minutes
    group_membership_cache: TTLCache = TTLCache(maxsize=100, ttl=60 * 5)

    def __init__(
        self,
        auth_client: ConfidentialAppAuthClient,
        bearer_token: str,
        expected_scopes: Iterable[str],
        expected_audience: Optional[str] = None,
    ) -> None:
        self.auth_client = auth_client
        self.bearer_token = bearer_token
        self.expected_scopes = expected_scopes

        # Default to client_id unless expected_audience has been explicitly
        # provided (supporting legacy clients that may have a different
        # client name registered with Auth)
        if expected_audience is None:
            self.expected_audience = auth_client.client_id
        else:
            self.expected_audience = expected_audience
        self.errors: List[Exception] = []
        self._groups_client: Optional[GroupsClient] = None

    def __repr__(self):
        # This repr is used in a cache key (see caching.py)
        # Be careful about changing it without testing
        # caching behavior.
        tmpl = "<AuthState for client_id='{}' with bearer_token='{}'>"
        return tmpl.format(self.auth_client.client_id, self.bearer_token)

    def introspect_token(self) -> Optional[GlobusHTTPResponse]:
        # There are cases where a null or empty string bearer token are present as a
        # placeholder
        if self.bearer_token is None:
            return None

        resp = AuthState.introspect_cache.get(self.bearer_token)
        if resp is not None:
            return resp

        resp = self.auth_client.oauth2_token_introspect(
            self.bearer_token, include="identity_set"
        )
        now = time()

        try:
            assert resp.get("active", False) is True, "Invalid token."
            assert resp.get("nbf", now + 4) < (
                time() + 3
            ), "Token not yet valid -- check system clock?"
            assert resp.get("exp", 0) > (time() - 3), "Token expired."
            scopes = frozenset(resp.get("scope", "").split())
            assert scopes.intersection(
                set(self.expected_scopes)
            ), f"Token invalid scopes. Expected one of: {self.expected_scopes}, got: {scopes}"
            aud = resp.get("aud", [])
            assert (
                self.expected_audience in aud
            ), f"Token not intended for us: audience={aud}, expected={self.expected_audience}"
            assert "identity_set" in resp, "Missing identity_set"
        except AssertionError as err:
            self.errors.append(err)
            log.info(err)
            return None
        else:
            AuthState.introspect_cache[self.bearer_token] = resp
            return resp

    @property
    def effective_identity(self) -> Optional[str]:
        tkn_details = self.introspect_token()
        if tkn_details is None:
            return None
        effective = identity_principal(tkn_details["sub"])
        return effective

    @property
    def identities(self) -> FrozenSet[str]:
        tkn_details = self.introspect_token()
        if tkn_details is None:
            return frozenset()
        return frozenset(map(identity_principal, tkn_details["identity_set"]))

    @property
    def principals(self) -> FrozenSet[str]:
        return self.identities.union(self.groups)

    @property  # type: ignore
    def groups(self) -> FrozenSet[str]:
        try:
            groups_client = self._get_groups_client()
            groups_token = groups_client.authorizer.access_token
            groups_set = AuthState.group_membership_cache.get(groups_token)
        except (GlobusAPIError, KeyError, ValueError) as err:
            # Only debug level, because this could be normal state of
            # affairs for a system that doesn't use or care about groups.
            log.debug(err)
            self.errors.append(err)
            return frozenset()
        else:
            if groups_set is not None:
                return groups_set

        try:
            groups = groups_client.list_groups()
        except GlobusError as err:
            log.exception(f"Error getting groups: {str(err)}")
            self.errors.append(err)
            return frozenset()
        else:
            groups_set = frozenset(map(group_principal, (grp["id"] for grp in groups)))
            AuthState.group_membership_cache[groups_token] = groups_set
            return groups_set

    @property
    def dependent_tokens_cache_id(self) -> Optional[str]:
        tkn_details = self.introspect_token()
        if tkn_details is None:
            return None
        return tkn_details.get("dependent_tokens_cache_id")

    def get_dependent_tokens(self) -> OAuthTokenResponse:
        """
        Returns OAuthTokenResponse representing the dependent tokens associated
        with a particular access token.
        """
        dependent_tokens_cache_id = self.dependent_tokens_cache_id
        if dependent_tokens_cache_id is not None:
            resp = AuthState.dependent_tokens_cache.get(dependent_tokens_cache_id)
            if resp is not None:
                return resp
        resp = self.auth_client.oauth2_get_dependent_tokens(
            self.bearer_token, {"access_type": "offline"}
        )
        if resp is not None and dependent_tokens_cache_id is not None:
            AuthState.dependent_tokens_cache[dependent_tokens_cache_id] = resp
        return resp

    def get_authorizer_for_scope(
        self, scope: str
    ) -> Optional[Union[RefreshTokenAuthorizer, AccessTokenAuthorizer]]:
        try:
            dep_tkn_resp = self.get_dependent_tokens().by_scopes[scope]
        except KeyError:
            return None

        if "refresh_token" in dep_tkn_resp:
            return RefreshTokenAuthorizer(
                dep_tkn_resp["refresh_token"],
                self.auth_client,
                access_token=dep_tkn_resp["access_token"],
                expires_at=dep_tkn_resp["expires_at_seconds"],
            )
        elif "access_token" in dep_tkn_resp:
            return AccessTokenAuthorizer(dep_tkn_resp["access_token"])
        else:
            return None

    def _get_groups_client(self) -> GroupsClient:
        if self._groups_client is not None:
            return self._groups_client
        authorizer = self.get_authorizer_for_scope(GROUPS_SCOPE)
        if authorizer is None:
            raise ValueError(f"Unable to get authorizor for {GROUPS_SCOPE}")

        self._groups_client = GroupsClient(authorizer=authorizer)
        return self._groups_client

    @staticmethod
    def group_in_principal_list(principal_list: Iterable[str]) -> bool:
        """Check a list of principals to determine if any of the are group based
        principals. Determined by looking for the urn:globus:groups:id prefix on any of
        the values.
        """
        return any(
            principal.startswith("urn:globus:groups:id") for principal in principal_list
        )

    def check_authorization(
        self,
        allowed_principals: Iterable[str],
        allow_public: bool = False,
        allow_all_authenticated_users: bool = False,
    ) -> bool:
        allowed_set = frozenset(allowed_principals)
        all_principals = self.identities
        # We only need to merge in the groups values to the principals list if there are
        # group principals in the list. Can save a round trip to the Groups service if
        # there's no need to check for group membership.
        if AuthState.group_in_principal_list(allowed_set):
            allowed_principals = set(allowed_principals).union(self.groups)
        if (
            (allow_public and "public" in allowed_set)
            or (allowed_set.intersection(all_principals))
            or (
                allow_all_authenticated_users
                and "all_authenticated_users" in allowed_set
                and len(self.identities) > 0
            )
        ):
            return True
        else:
            return False


class TokenChecker:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        expected_scopes: Iterable[str],
        expected_audience: Optional[str] = None,
        cache_config: Optional[dict] = None,
    ) -> None:
        self.auth_client = ConfidentialAppAuthClient(client_id, client_secret)
        self.default_expected_scopes = frozenset(expected_scopes)

        if expected_audience is None:
            self.expected_audience = client_id
        else:
            self.expected_audience = expected_audience

        # Try to check a 'token' and fail fast here in case client_id/secret are bad:
        try:
            self.check_token("NotAToken").introspect_token()
        except GlobusAPIError as err:
            if err.http_status == 401:
                raise ConfigurationError("Check client_id and client_secret", err)

    def check_token(
        self, access_token: str, expected_scopes: Iterable[str] = None
    ) -> AuthState:
        if expected_scopes is None:
            expected_scopes = self.default_expected_scopes
        else:
            expected_scopes = frozenset(expected_scopes)
        return AuthState(
            self.auth_client, access_token, expected_scopes, self.expected_audience
        )
