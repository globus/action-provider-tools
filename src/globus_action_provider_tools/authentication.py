from __future__ import annotations

import functools
import hashlib
import logging
import warnings
from typing import Iterable

import globus_sdk
from globus_sdk import (
    AccessTokenAuthorizer,
    ConfidentialAppAuthClient,
    GlobusHTTPResponse,
)

from .utils import TypedTTLCache

log = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    """Return a hash of the token, suitable for use as a cache key"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def group_principal(id_: str) -> str:
    return f"urn:globus:groups:id:{id_}"


def identity_principal(id_: str) -> str:
    return f"urn:globus:auth:identity:{id_}"


class InvalidTokenScopesError(ValueError):
    def __init__(
        self, expected_scopes: frozenset[str], actual_scopes: frozenset[str]
    ) -> None:
        self.expected_scopes = expected_scopes
        self.actual_scopes = actual_scopes
        super().__init__(
            f"Token scopes were not valid. "
            f"The valid scopes for this service are {self.expected_scopes} but the "
            f"token contained {self.actual_scopes} upon inspection."
        )


class InactiveTokenError(ValueError):
    """Indicates that the token is not valid (its 'active' field is False)."""


class AuthState:
    # Cache for introspection operations, max lifetime: 30 seconds
    introspect_cache: TypedTTLCache[globus_sdk.GlobusHTTPResponse] = TypedTTLCache(
        maxsize=100, ttl=30
    )

    # Cache for dependent tokens, max lifetime: 47 hours: a bit less than the 48 hours
    # for which an access token is valid
    dependent_tokens_cache: TypedTTLCache[globus_sdk.OAuthDependentTokenResponse] = (
        TypedTTLCache(maxsize=100, ttl=47 * 3600)
    )

    # Cache for group lookups, max lifetime: 5 minutes
    group_membership_cache: TypedTTLCache[frozenset[str]] = TypedTTLCache(
        maxsize=100, ttl=60 * 5
    )

    def __init__(
        self,
        auth_client: ConfidentialAppAuthClient,
        bearer_token: str,
        expected_scopes: frozenset[str],
    ) -> None:
        self.auth_client = auth_client
        self.bearer_token = bearer_token
        self.sanitized_token = self.bearer_token[-7:]
        self.expected_scopes = expected_scopes

        self.errors: list[Exception] = []
        self._groups_client: globus_sdk.GroupsClient | None = None

    @functools.cached_property
    def _token_hash(self) -> str:
        return _hash_token(self.bearer_token)

    @functools.cached_property
    def _dependent_token_cache_key(self) -> str:
        # Caching is done based on a hash of the token string, **not** the
        # dependent_tokens_cache_id.
        # This guarantees that we get a new access token for any upstream service
        # calls if we get a new token, which is helpful for cache busting.
        return f"dependent_tokens:{_hash_token(self.bearer_token)}"

    def _cached_introspect_call(self) -> GlobusHTTPResponse:
        introspect_result = AuthState.introspect_cache.get(self._token_hash)
        if introspect_result is not None:
            log.debug(
                f"Using cached introspection response for token_hash={self._token_hash}"
            )
            return introspect_result

        log.debug(f"Introspecting token <token_hash={self._token_hash}>")
        introspect_result = self.auth_client.oauth2_token_introspect(
            self.bearer_token, include="identity_set"
        )
        self.introspect_cache[self._token_hash] = introspect_result

        return introspect_result

    def introspect_token(self) -> GlobusHTTPResponse:
        introspect_result = self._cached_introspect_call()
        self._verify_introspect_result(introspect_result)
        return introspect_result

    def _verify_introspect_result(self, introspect_result: GlobusHTTPResponse) -> None:
        """
        A helper which checks token introspect properties and raises exceptions on failure.
        """

        if not introspect_result["active"]:
            raise InactiveTokenError("The token is invalid.")

        # validate scopes, ensuring that the token provided accords with the service's
        # notion of what operations exist and are supported
        scopes = frozenset(introspect_result.get("scope", "").split())
        if not scopes.issuperset(self.expected_scopes):
            raise InvalidTokenScopesError(self.expected_scopes, scopes)

    @property
    def effective_identity(self) -> str:
        tkn_details = self.introspect_token()
        effective = identity_principal(tkn_details["sub"])
        return effective

    @property
    def identities(self) -> frozenset[str]:
        tkn_details = self.introspect_token()
        return frozenset(map(identity_principal, tkn_details["identity_set"]))

    @property
    def principals(self) -> frozenset[str]:
        return self.identities.union(self.groups)

    @property
    def groups(self) -> frozenset[str]:
        group_set: frozenset[str] | None = self.group_membership_cache.get(
            self._token_hash
        )
        if group_set is None:
            try:
                groups_client = self._get_groups_client()
            except (globus_sdk.GlobusAPIError, KeyError, ValueError) as err:
                # Only warning level, because this could be normal state of
                # affairs for a system that doesn't use or care about groups.
                log.warning(
                    "Unable to determine groups membership. Setting groups to {}",
                    exc_info=True,
                )
                self.errors.append(err)
                return frozenset()

            try:
                group_data = groups_client.get_my_groups()
            except globus_sdk.GlobusAPIError:
                log.warning(
                    "failed to get groups, treating groups as '{}'", exc_info=True
                )
                return frozenset()

            group_set = frozenset(group_principal(g["id"]) for g in group_data)
            self.group_membership_cache[self._token_hash] = group_set
        return group_set

    def get_dependent_tokens(
        self, *, bypass_cache_lookup: bool = False
    ) -> globus_sdk.OAuthDependentTokenResponse:
        """
        Returns OAuthTokenResponse representing the dependent tokens associated
        with a particular access token.
        """
        # TODO: consider deprecating and removing this method
        # it is no longer used by `get_authorizer_for_scope()`, which now uses logic which cannot
        # be satisfied by the contract provided by this method

        if not bypass_cache_lookup:
            resp = self.dependent_tokens_cache.get(self._dependent_token_cache_key)
            if resp is not None:
                log.info(
                    f"Using cached dependent token response (key={self._dependent_token_cache_key})"
                )
                return resp

        log.info(f"Doing a dependent token grant for token ***{self.sanitized_token}")
        resp = self.auth_client.oauth2_get_dependent_tokens(
            self.bearer_token, additional_params={"access_type": "offline"}
        )
        log.info(
            f"Caching dependent token response for token ***{self.sanitized_token}"
        )
        self.dependent_tokens_cache[self._dependent_token_cache_key] = resp
        return resp

    def get_authorizer_for_scope(
        self,
        scope: str,
        required_authorizer_expiration_time: int | None = None,
    ) -> AccessTokenAuthorizer:
        """
        Get dependent tokens for the caller's token, then retrieve token data for the
        requested scope and attempt to build an authorizer from that data.

        The class caches dependent token results, regardless of whether or not
        building authorizers succeeds.

        :param scope: The scope for which an authorizer is being requested
        :param required_authorizer_expiration_time: Deprecated parameter. Has no effect.
        """
        if required_authorizer_expiration_time is not None:
            warnings.warn(
                "`required_authorizer_expiration_time` has no effect and will be removed in a future version.",
                DeprecationWarning,
                stacklevel=2,
            )

        retrieved_from_cache, dependent_tokens = self._get_cached_dependent_tokens()

        # if the dependent token data (which could have been cached) failed to meet
        # the scope requirement...
        if scope not in dependent_tokens.by_scopes:
            # if there was no cached value, we just got fresh dependent tokens
            # to do this work but the scope was missing
            # there's no reason to expect new tokens would do better
            # fail, but do not clear the cache
            if not retrieved_from_cache:
                raise ValueError("Dependent tokens do not match request.")

            # otherwise, the cached value was bad -- fetch and check again,
            # by clearing the cache and asking for the same data
            del self.dependent_tokens_cache[self._dependent_token_cache_key]
            _, dependent_tokens = self._get_cached_dependent_tokens()

            # check scope again -- this is guaranteed to be fresh data
            if scope not in dependent_tokens.by_scopes:
                raise ValueError("Dependent tokens do not match request.")

        token_data = dependent_tokens.by_scopes[scope]
        return AccessTokenAuthorizer(token_data["access_token"])

    def _get_cached_dependent_tokens(
        self,
    ) -> tuple[bool, globus_sdk.OAuthDependentTokenResponse]:
        """
        Get dependent token data, potentially from cache.
        Return the data paired with a bool indicating whether or not the value was
        cached or a fresh callout.
        """
        if self._dependent_token_cache_key in self.dependent_tokens_cache:
            return (True, self.dependent_tokens_cache[self._dependent_token_cache_key])
        token_response = self.auth_client.oauth2_get_dependent_tokens(self.bearer_token)
        self.dependent_tokens_cache[self._dependent_token_cache_key] = token_response
        return (False, token_response)

    def _get_groups_client(self) -> globus_sdk.GroupsClient:
        if self._groups_client is not None:
            return self._groups_client
        authorizer = self.get_authorizer_for_scope(
            globus_sdk.GroupsClient.scopes.view_my_groups_and_memberships
        )
        self._groups_client = globus_sdk.GroupsClient(authorizer=authorizer)
        return self._groups_client

    @staticmethod
    def group_in_principal_list(principal_list: Iterable[str]) -> bool:
        """Check a list of principals to determine if any of them are group-based
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
        """Check whether an incoming request is authorized."""

        # Note: These conditions are ordered to reduce I/O with Globus Auth.

        # If the action provider is publicly available, the request is authorized.
        allowed_set = set(allowed_principals)
        if allow_public and "public" in allowed_set:
            return True

        # If the action provider is available to all authenticated users,
        # any successful token introspection will be sufficient authorization.
        all_principals = self.identities  # I/O call, possibly cached
        if (
            allow_all_authenticated_users
            and "all_authenticated_users" in allowed_set
            and all_principals
        ):
            return True

        # If the action provider's access list includes group principals,
        # an additional call to Globus Auth is needed to get the user's groups.
        if AuthState.group_in_principal_list(allowed_set):
            all_principals |= self.groups  # I/O call, possibly cached

        return bool(allowed_set & all_principals)


class AuthStateBuilder:
    def __init__(
        self,
        auth_client: globus_sdk.ConfidentialAppAuthClient,
        expected_scopes: Iterable[str],
    ) -> None:
        self.auth_client = auth_client
        self.default_expected_scopes = frozenset(expected_scopes)

    def build(
        self, access_token: str, expected_scopes: Iterable[str] | None = None
    ) -> AuthState:
        if expected_scopes is None:
            expected_scopes = self.default_expected_scopes
        else:
            expected_scopes = frozenset(expected_scopes)
        return AuthState(self.auth_client, access_token, expected_scopes)
