from __future__ import annotations

import logging
import time
import typing as t

import globus_sdk
from cachetools import TTLCache

log = logging.getLogger(__name__)


def group_principal(id_: str) -> str:
    return f"urn:globus:groups:id:{id_}"


def identity_principal(id_: str) -> str:
    return f"urn:globus:auth:identity:{id_}"


class AuthenticationFailed(RuntimeError):
    pass


class AuthStateResponseCache:
    def get_introspect(self, token: str) -> globus_sdk.GlobusHTTPResponse | None:
        return None

    def store_introspect(
        self, token: str, response: globus_sdk.GlobusHTTPResponse
    ) -> None:
        pass

    def get_dependent_tokens(
        self, cache_id: str
    ) -> globus_sdk.OAuthDependentTokenResponse | None:
        return None

    def store_dependent_tokens(
        self, cache_id: str, response: globus_sdk.OAuthDependentTokenResponse
    ) -> None:
        pass

    def get_groups(self, cache_id: str) -> globus_sdk.GlobusHTTPResponse | None:
        return None

    def store_groups(
        self, cache_id: str, response: globus_sdk.GlobusHTTPResponse
    ) -> None:
        pass


class CachetoolsAuthStateResponseCache(AuthStateResponseCache):
    def __init__(self) -> None:
        # Cache for introspection operations, max lifetime: 30 seconds
        self._introspect_cache: t.MutableMapping[
            str, globus_sdk.GlobusHTTPResponse
        ] = TTLCache(maxsize=100, ttl=30)
        # Cache for dependent tokens, max lifetime: 47 hours: a bit less than
        # the 48 hours until a refresh would be required anyway
        self._dependent_tokens_cache: t.MutableMapping[
            str, globus_sdk.OAuthDependentTokenResponse
        ] = TTLCache(maxsize=100, ttl=47 * 3600)
        # Cache for group lookups, max lifetime: 1 minute
        self._group_membership_cache: t.MutableMapping[
            str,
            # TODO: update to globus_sdk.ArrayResponse (not currently exported)
            globus_sdk.GlobusHTTPResponse,
        ] = TTLCache(maxsize=100, ttl=60)

    def get_introspect(self, token: str) -> globus_sdk.GlobusHTTPResponse | None:
        return self._introspect_cache.get(token)

    def store_introspect(
        self, token: str, response: globus_sdk.GlobusHTTPResponse
    ) -> None:
        self._introspect_cache[token] = response

    def get_dependent_tokens(
        self, cache_id: str
    ) -> globus_sdk.OAuthDependentTokenResponse | None:
        return self._dependent_tokens_cache.get(cache_id)

    def store_dependent_tokens(
        self, cache_id: str, response: globus_sdk.OAuthDependentTokenResponse
    ) -> None:
        self._dependent_tokens_cache[cache_id] = response

    def get_groups(self, cache_id: str) -> globus_sdk.GlobusHTTPResponse | None:
        return self._group_membership_cache.get(cache_id)

    def store_groups(
        self, cache_id: str, response: globus_sdk.GlobusHTTPResponse
    ) -> None:
        self._group_membership_cache[cache_id] = response


class AuthState:
    #: scopes which the token must have
    VALID_SCOPES: t.ClassVar[t.FrozenSet[str]] = frozenset()
    #: an expectation for the "aud" field
    EXPECTED_AUDIENCE: t.ClassVar[str | None] = None
    #: require that the user's group memberships are included in AuthState
    #: note that this has no bearing on unauthenticated calls (when the token is None)
    REQUIRE_GROUP_LISTING: t.ClassVar[bool] = False

    def __init__(
        self,
        *,
        auth_client: globus_sdk.ConfidentialAppAuthClient,
        token: str | None,
        response_cache: AuthStateResponseCache | None = None,
    ) -> None:
        self.auth_client = auth_client
        self.token = token
        self.response_cache: AuthStateResponseCache = (
            response_cache or CachetoolsAuthStateResponseCache()
        )

        # collect attributes from the inspection of token and group data
        # this eagerly calls out to external services:
        #  - Globus Auth token introspect is called to get token data
        #  - Globus Auth dependent tokens is called to check for the presence of
        #    dependent tokens
        #  - if a dependent Groups token is found, Globus Groups get_my_groups is called
        #    to get a list of groups
        self._introspect_data: globus_sdk.GlobusHTTPResponse | None = None
        self._groups_client: globus_sdk.GroupsClient | None = None
        self._dependent_tokens_cache_id: str | None = None
        self.effective_identity: str | None = None
        self.identities: t.FrozenSet[str] = frozenset()
        self.groups: t.FrozenSet[str] = frozenset()
        self.principals: t.FrozenSet[str] = frozenset()
        if self.token is not None:
            # introspect the token and set the dervied attributes
            self._introspect_data = self._introspect_token(self.token)
            self._dependent_tokens_cache_id = self._introspect_data.get(
                "dependent_tokens_cache_id"
            )
            self.effective_identity = identity_principal(self._introspect_data["sub"])
            self.identities = frozenset(
                [identity_principal(i) for i in self._introspect_data["identity_set"]]
            )

            # get group info and set derived attributes
            self._groups_client = self._create_groups_client()
            self.groups = frozenset(self._list_groups())

            # set attributes which are derived from groups + introspect
            self.principals = self.identities.union(self.groups)

    @property
    def is_authenticated(self) -> bool:
        return self._introspect_data is not None

    def _introspect_token(self, token: str) -> globus_sdk.GlobusHTTPResponse:
        response = self.response_cache.get_introspect(token)
        if response is not None:
            log.debug("Using cached introspect")
            return response

        log.debug("Introspecting token")
        response = self.auth_client.oauth2_token_introspect(
            self.token, include="identity_set"
        )

        self._validate_introspect_response(response)

        log.debug("Caching token response")
        self.response_cache.store_introspect(token, response)
        return response

    def _list_groups(self) -> list[str]:
        if self._groups_client is None:
            if self.REQUIRE_GROUP_LISTING:
                raise AuthenticationFailed(
                    "REQUIRE_GROUP_LISTING=true but a groups client was not available"
                )
            log.info("Unable to determine groups membership. Setting groups to {}")
            return []

        # TODO: determine if this is the right caching strategy, caching on the
        # effective identity ID
        # we could also use a hash of the incoming token, the dependent token cache ID,
        # or some other cache key
        cache_key = self.effective_identity
        assert cache_key is not None  # should be impossible, explain to mypy

        response = self.response_cache.get_groups(cache_key)
        if response is not None:
            log.debug(f"Using cached group membership for {cache_key}")
        else:
            log.info(f"Querying group list for {cache_key}")
            response = self._groups_client.get_my_groups()
            log.info(f"Caching groups for {cache_key}")
            self.response_cache.store_groups(cache_key, response)
        return list([g["id"] for g in response])

    def _validate_introspect_response(
        self, response: globus_sdk.GlobusHTTPResponse
    ) -> None:
        now = time.time()

        errors: list[str] = []

        if not response.get("active", False):
            errors.append("token is not active")

        nbf = response.get("nbf", now + 1)
        if nbf > now:
            errors.append(f"token not yet valid (nbf={nbf})")
        exp = response.get("exp", 0)
        if exp < now:
            errors.append(f"token expired (exp={exp})")

        if self.VALID_SCOPES:
            scopes = response.get("scope", "").split()
            if any(s not in self.VALID_SCOPES for s in scopes):
                errors.append(
                    "got token with invalid scopes, "
                    f"expected a subset of {list(self.VALID_SCOPES)} "
                    f"but got {scopes}"
                )

        if self.EXPECTED_AUDIENCE is not None:
            aud = response.get("aud", [])
            if self.EXPECTED_AUDIENCE not in aud:
                errors.append(
                    f"Token not intended for us: audience={aud}, "
                    f"expected={self.EXPECTED_AUDIENCE}"
                )

        if errors:
            raise AuthenticationFailed("; ".join(errors))

    def _create_groups_client(self) -> globus_sdk.GroupsClient | None:
        """try to build a client, but on failure, failover to None"""
        dep_tokens = self.get_dependent_tokens().by_resource_server
        if globus_sdk.GroupsClient.resource_server not in dep_tokens:
            if self.REQUIRE_GROUP_LISTING:
                raise AuthenticationFailed(
                    "Could not build GroupsClient due to missing dependent token"
                )
            return None

        groups_token_data = dep_tokens[globus_sdk.GroupsClient.resource_server]
        return globus_sdk.GroupsClient(
            authorizer=globus_sdk.AccessTokenAuthorizer(
                groups_token_data["access_token"]
            )
        )

    def get_dependent_tokens(self) -> globus_sdk.OAuthDependentTokenResponse:
        """
        Returns OAuthTokenResponse representing the dependent tokens associated
        with a particular access token.
        """
        if self._dependent_tokens_cache_id is not None:
            response = self.response_cache.get_dependent_tokens(
                self._dependent_tokens_cache_id
            )

            if response is not None:
                log.debug(
                    "Using cached dependent token response with cache ID "
                    f"{self._dependent_tokens_cache_id}"
                )
                return response

        log.info("Doing a dependent token grant")
        response = self.auth_client.oauth2_get_dependent_tokens(self.token)
        if self._dependent_tokens_cache_id is not None:
            log.info("Caching dependent token response")
            self.response_cache.store_dependent_tokens(
                self._dependent_tokens_cache_id, response
            )
        return response

    # TODO: determine whether or not this helper should be removed?
    def check_authorization(
        self,
        allowed_principals: set[str],
        allow_public: bool = False,
        allow_all_authenticated_users: bool = False,
    ) -> bool:
        if allow_public and "public" in allowed_principals:
            return True
        if (
            allow_all_authenticated_users
            and "all_authenticated_users" in allowed_principals
            and len(self.identities) > 0
        ):
            return True

        if allowed_principals.intersection(self.principals):
            return True

        return False


A = t.TypeVar("A", bound=AuthState)


class AuthStateFactory(t.Generic[A]):
    @t.overload
    def __init__(
        self: AuthStateFactory[AuthState],
        *,
        auth_client: globus_sdk.ConfidentialAppAuthClient,
    ) -> None:
        ...

    @t.overload
    def __init__(
        self: AuthStateFactory[A],
        *,
        auth_client: globus_sdk.ConfidentialAppAuthClient,
        state_class: type[A],
    ) -> None:
        ...

    def __init__(self, *, auth_client, state_class=AuthState) -> None:
        self.auth_client = auth_client
        self.state_class = state_class

    def make_state(self, token: str | None) -> A:
        return self.state_class(auth_client=self.auth_client, token=token)

    def parse_authorization_header(self, headers: t.Mapping[str, str]) -> A:
        token: str | None = None

        authorization_header = headers.get("Authorization", "").strip()
        if authorization_header.startswith("Bearer "):
            token = authorization_header[len("Bearer ") :]

        return self.make_state(token)
