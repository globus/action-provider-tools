from unittest.mock import Mock, patch

import pytest
from globus_sdk import AccessTokenAuthorizer, AuthAPIError
from globus_sdk.response import GlobusHTTPResponse

from globus_action_provider_tools.authentication import (
    GROUPS_SCOPE,
    AuthState,
    ConfigurationError,
    TokenChecker,
    identity_principal,
)
from globus_action_provider_tools.groups_client import GroupsClient

from .data import canned_responses


def new_groups_client(auth_client, upstream_token):
    resp = auth_client.oauth2_get_dependent_tokens(
        upstream_token, {"access_type": "offline"}
    ).by_scopes[GROUPS_SCOPE]
    authz = AccessTokenAuthorizer(resp["access_token"])
    return GroupsClient(authorizer=authz)


@pytest.fixture
def invalid_token(live_api, monkeypatch):
    if live_api:
        return
    else:
        fake_introspect = Mock(
            return_value=GlobusHTTPResponse(canned_responses.resp({"active": False}))
        )
        monkeypatch.setattr(AuthState, "introspect_token", fake_introspect)


@pytest.fixture
def bad_credentials_error(live_api, monkeypatch):
    if live_api:
        return
    resp = canned_responses.resp({"error": "invalid_client"}, 401)
    fake_introspect = Mock(side_effect=AuthAPIError(resp))
    monkeypatch.setattr(AuthState, "introspect_token", fake_introspect)


def test_token_checker_bad_credentials():
    with pytest.raises(ConfigurationError):
        TokenChecker(
            client_id="bogus",
            client_secret="bogus",
            expected_scopes=("fakescope",),
        )


def test_get_identities(auth_state):
    resp = canned_responses.introspect_response()()
    assert len(auth_state.identities) == len(resp.get("identity_set"))
    assert all(i.startswith("urn:globus:auth:identity") for i in auth_state.identities)


def test_get_groups(auth_state):
    expected_groups = canned_responses.groups_response()()
    assert len(auth_state.groups) == len(expected_groups)
    assert all(g.startswith("urn:globus:groups:id:") for g in auth_state.groups)


def test_effective_identity(auth_state):
    expected = canned_responses.mock_effective_identity()
    expected = identity_principal(expected)
    assert auth_state.effective_identity == expected


def test_caching_identities(auth_state):
    for i in range(3):
        auth_state.identities
        auth_state.effective_identity

    assert auth_state.auth_client.oauth2_token_introspect.call_count == 1


def test_caching_groups(auth_state):
    for i in range(3):
        auth_state.groups

    assert auth_state.auth_client.oauth2_get_dependent_tokens.call_count == 1
    assert auth_state._groups_client.list_groups.call_count == 1
