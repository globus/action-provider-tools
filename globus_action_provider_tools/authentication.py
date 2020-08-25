import logging
from time import time
from typing import FrozenSet, Iterable, List, Optional

from globus_sdk import ConfidentialAppAuthClient
from globus_sdk.auth.token_response import OAuthTokenResponse
from globus_sdk.authorizers import (
    AccessTokenAuthorizer,
    GlobusAuthorizer,
    RefreshTokenAuthorizer,
)
from globus_sdk.exc import GlobusAPIError, GlobusError
from globus_sdk.response import GlobusHTTPResponse

from .caching import DEFAULT_CACHE_BACKEND, DEFAULT_CACHE_TIMEOUT, dogpile_cache
from .errors import ConfigurationError, TokenValidationError
from .groups_client import GroupsClient

log = logging.getLogger(__name__)


def group_principal(id_):
    return "urn:globus:groups:id:" + id_


def identity_principal(id_):
    return "urn:globus:auth:identity:" + id_


GROUPS_SCOPE = (
    "urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships"
)


class AuthState(object):
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
        # NB: expected_audience can be removed once
        # https://github.com/globusonline/globus-auth/issues/1527
        # is completed
        # UPDATE: Above issue has been implemented, so defaulting now to the client_id
        # unless explicitly provided (supporting legacy clients that may have a different
        # client name registered with Auth)
        if expected_audience is not None:
            self.expected_audience = expected_audience
        else:
            self.expected_audience = auth_client.client_id
        self.errors: List[Exception] = []
        self._groups_client: Optional[GroupsClient] = None

    def __repr__(self):
        # This repr is used in a cache key (see caching.py)
        # Be careful about changing it without testing
        # caching behavior.
        tmpl = "<AuthState for client_id='{}' with bearer_token='{}'>"
        return tmpl.format(self.auth_client.client_id, self.bearer_token)

    @dogpile_cache.cache_on_arguments()
    def introspect_token(self) -> Optional[GlobusHTTPResponse]:
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
            ), f"Token not intended for us: audience={aud}"
            assert "identity_set" in resp, "Missing identity_set"
        except AssertionError as err:
            our_err = TokenValidationError(err)
            self.errors.append(our_err)
            log.info(our_err)
            return None
        else:
            log.debug(resp)
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

    @property  # type: ignore
    @dogpile_cache.cache_on_arguments()
    def groups(self) -> FrozenSet[str]:
        try:
            groups_client = self._get_groups_client()
        except (GlobusAPIError, KeyError, ValueError) as err:
            # Only debug level, because this could be normal state of
            # affairs for a system that doesn't use or care about groups.
            log.debug(err)
            self.errors.append(err)
            return frozenset()

        try:
            groups = groups_client.list_groups()
        except GlobusError as err:
            log.exception(f"Error getting groups: {str(err)}")
            self.errors.append(err)
            return frozenset()
        else:
            return frozenset(map(group_principal, (grp["id"] for grp in groups)))

    @dogpile_cache.cache_on_arguments(expiration_time=86400)  # 24 hours
    def get_dependent_tokens(self) -> OAuthTokenResponse:
        """
        Returns OAuthTokenResponse representing the dependent tokens associated
        with a particular access token.
        """
        return self.auth_client.oauth2_get_dependent_tokens(
            self.bearer_token, {"access_type": "offline"}
        )

    def get_authorizer_for_scope(self, scope: str) -> Optional[GlobusAuthorizer]:
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
        else:
            self._groups_client = GroupsClient(authorizer=authorizer)
        return self._groups_client

    def check_authorization(
        self,
        allowed_principals: Iterable[str],
        allow_public: bool = False,
        allow_all_authenticated_users: bool = False,
    ) -> bool:
        allowed_set = frozenset(allowed_principals)
        all_principals = self.identities.union(self.groups)
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

        if cache_config:
            dogpile_cache.configure(
                backend=cache_config.pop("backend", DEFAULT_CACHE_BACKEND),
                expiration_time=cache_config.pop("timeout", DEFAULT_CACHE_TIMEOUT),
                arguments=cache_config,
                replace_existing_backend=True,
            )

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
