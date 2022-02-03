import logging
from time import time
from typing import FrozenSet, Iterable, List, Optional, Union, cast

from cachetools import TTLCache
from globus_sdk import (
    AccessTokenAuthorizer,
    ConfidentialAppAuthClient,
    GlobusAPIError,
    GlobusError,
    GlobusHTTPResponse,
    RefreshTokenAuthorizer,
)
from globus_sdk.services.auth import OAuthTokenResponse

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

    # Cache for dependent tokens, max lifetime: 47 hours: a bit less than the 48 hours
    # until a refresh would be required anyway
    dependent_tokens_cache: TTLCache = TTLCache(maxsize=100, ttl=47 * 3600)

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
        self.sanitized_token = self.bearer_token[-7:]
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

    def introspect_token(self) -> Optional[GlobusHTTPResponse]:
        # There are cases where a null or empty string bearer token are present as a
        # placeholder
        if self.bearer_token is None:
            return None

        resp = AuthState.introspect_cache.get(self.bearer_token)
        if resp is not None:
            log.info(
                f"Using cached introspection response for token ***{self.sanitized_token}"
            )
            return resp

        log.info(f"Introspecting token ***{self.sanitized_token}")
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
            log.info(f"Caching token response for token ***{self.sanitized_token}")
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
        except (GlobusAPIError, KeyError, ValueError) as err:
            # Only warning level, because this could be normal state of
            # affairs for a system that doesn't use or care about groups.
            log.warning(
                "Unable to determine groups membership. Setting groups to {}",
                exc_info=True,
            )
            self.errors.append(err)
            return frozenset()
        else:
            try:
                groups_token = getattr(groups_client.authorizer, "access_token")
            except AttributeError as err:
                log.error("Missing access token to use for groups service")
                self.errors.append(err)
                return frozenset()
            safe_groups_token = groups_token[-7:]
            groups_set = AuthState.group_membership_cache.get(groups_token)
            if groups_set is not None:
                log.info(
                    f"Using cached group membership for groups token ***{safe_groups_token}"
                )
                return groups_set

        try:
            log.info(f"Querying groups for groups token ***{safe_groups_token}")
            groups = groups_client.list_groups()
        except GlobusError as err:
            log.exception("Error getting groups", exc_info=True)
            self.errors.append(err)
            return frozenset()
        else:
            groups_set = frozenset(map(group_principal, (grp["id"] for grp in groups)))
            log.info(f"Caching groups for token **{safe_groups_token}")
            AuthState.group_membership_cache[groups_token] = groups_set
            return groups_set

    @property
    def dependent_tokens_cache_id(self) -> Optional[str]:
        tkn_details = self.introspect_token()
        if tkn_details is None:
            return None
        return tkn_details.get("dependent_tokens_cache_id")

    def get_dependent_tokens(self, bypass_cache_lookup=False) -> OAuthTokenResponse:
        """
        Returns OAuthTokenResponse representing the dependent tokens associated
        with a particular access token.
        """
        dependent_tokens_cache_id = self.dependent_tokens_cache_id
        if dependent_tokens_cache_id is not None and not bypass_cache_lookup:
            resp = AuthState.dependent_tokens_cache.get(dependent_tokens_cache_id)
            if resp is not None:
                log.info(
                    f"Using cached dependent token response with cache ID {dependent_tokens_cache_id} "
                    f"for token ***{self.sanitized_token}"
                )
                return resp

        log.info(f"Doing a dependent token grant for token ***{self.sanitized_token}")
        resp = self.auth_client.oauth2_get_dependent_tokens(
            self.bearer_token, additional_params={"access_type": "offline"}
        )
        if resp is not None and dependent_tokens_cache_id is not None:
            log.info(
                f"Caching dependent token response for token ***{self.sanitized_token}"
            )
            AuthState.dependent_tokens_cache[dependent_tokens_cache_id] = resp
        return resp

    def get_authorizer_for_scope(
        self,
        scope: str,
        bypass_dependent_token_cache=False,
        required_authorizer_expiration_time: int = 60,
    ) -> Optional[Union[RefreshTokenAuthorizer, AccessTokenAuthorizer]]:
        """Retrieve a Globus SDK authorizer for use in accessing a further Globus Auth registered
        service / "resource server". This authorizer can be passed to any Globus SDK
        Client class for use in accessing the Client's service.

        The authorizer is created by first performing a Globus Auth dependent token grant
        and looking for the requested scope in the set of tokens returned by the
        grant. If a refresh token is present in the grant response, a
        RefreshTokenAuthorizer is returned. If no refresh token is present, but an access
        token is present, an AccessTokenAuthorizer will be returned.

        A returned AccessTokenAuthorizer is guaranteed to be usable for at least the
        value passed in via required_authorizer_expiration_time which defaults to 60
        seconds. This implies that the authorizer, and the client created from it will be
        usable for at least this long. It is possible that the access token in the
        authorizer may expire after a time greater than this limit.

        If no dependent tokens can be generated for the requested scope, a None value is
        returned.

        To avoid redundant calls to perform dependent token grants, the class
        caches dependent token results for a particular incoming Bearer token used to
        access this Action Provider.

        If for any reason the caller of this function does not want to use a cached
        result, but would require that a new dependent grant is performed, the
        bypass_dependent_token_cache parameter may be set to True. This is used
        automatically in a case where an access token retrieved from cache is already
        expired: the function is called recursively to perform a new dependent token
        grant to get a new, valid token (even though bypass is set, the new token value
        will be added to the cache).

        """
        try:
            dep_tkn_resp = self.get_dependent_tokens(
                bypass_cache_lookup=bypass_dependent_token_cache
            ).by_scopes[scope]
        except KeyError:
            log.warning(
                f"Unable to create GlobusAuthorizer for scope {scope}. Using 'None'",
                exc_info=True,
            )
            return None

        refresh_token = cast(str, dep_tkn_resp.get("refresh_token"))
        access_token = cast(str, dep_tkn_resp.get("access_token"))
        token_expiration = dep_tkn_resp.get("expires_at_seconds", 0)
        # IF for some reason the token_expiration comes in a string, or even a string
        # containing a float representation, try converting to a proper int. If the
        # conversion is impossible, set expiration to 0 which should force some sort of
        # refresh as described elsewhere.
        if not isinstance(token_expiration, int):
            try:
                token_expiration = int(float(token_expiration))
            except ValueError:
                token_expiration = 0
        now = time()

        # IF we have an access token, we'll try building an authorizer from it if it is
        # valid long enough
        if access_token is not None:
            # If the access token will not expire for at least the required expiration
            # time, we return an authorizer based on that access token.
            if token_expiration > (int(now) + required_authorizer_expiration_time):
                log.debug(f"Creating an AccessTokenAuthorizer for scope {scope}")
                return AccessTokenAuthorizer(access_token)
            elif refresh_token is not None:
                # If the access token is going to expire, but we have a refresh token, ew
                # build an authorizer using the refresh token which will, in turn, perform
                # token refresh when needed.

                log.debug(f"Creating a RefreshTokenAuthorizer for scope {scope}")
                return RefreshTokenAuthorizer(
                    refresh_token,
                    self.auth_client,
                    access_token=access_token,
                    expires_at=token_expiration,
                )
            elif not bypass_dependent_token_cache:
                # If we aren't already trying to force a new grant by bypassing the
                # cache, try again to find a usable token, but bypass the cache so we
                # force a new dependent grant
                return self.get_authorizer_for_scope(
                    scope,
                    bypass_dependent_token_cache=True,
                    required_authorizer_expiration_time=required_authorizer_expiration_time,
                )

        # Fall through and haven't been able to create an authorizer, so return
        # none
        log.warning(
            f"Unable to create GlobusAuthorizer for scope {scope}. Using 'None'"
        )
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
