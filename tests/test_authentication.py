import typing
from unittest.mock import Mock

import pytest
from globus_sdk import (
    AccessTokenAuthorizer,
    AuthAPIError,
    GlobusHTTPResponse,
    GroupsClient,
)

from globus_action_provider_tools.authentication import (
    AuthState,
    TokenChecker,
    identity_principal,
)
from globus_action_provider_tools.errors import ConfigurationError

from .data import canned_responses


def new_groups_client(auth_client, upstream_token):
    resp = auth_client.oauth2_get_dependent_tokens(
        upstream_token, {"access_type": "offline"}
    ).by_scopes[GroupsClient.scopes.view_my_groups_and_memberships]
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
    num_test_calls = 3
    for i in range(num_test_calls):
        auth_state.identities
        auth_state.effective_identity

    # As the cache is global, we may have cached state from a previous test run meaning
    # that this test may never hit the actual (Mocked) Auth API call. We set the
    # condition for success to anything less than the total number of calls made
    assert auth_state.auth_client.oauth2_token_introspect.call_count < num_test_calls


def test_caching_groups(auth_state):
    num_test_calls = 3
    for i in range(num_test_calls):
        auth_state.groups

    # See above in test_cachine_identities for a description of the test for this
    # assertion
    assert (
        auth_state.auth_client.oauth2_get_dependent_tokens.call_count < num_test_calls
    )
    assert auth_state._groups_client.get_my_groups.call_count < num_test_calls


# for some reason mypy thinks introspect is not a mock
@typing.no_type_check
def test_duplicate_auth_state(auth_state: AuthState, duplicate_auth_state: AuthState):
    assert duplicate_auth_state is not auth_state
    introspect = duplicate_auth_state.auth_client.oauth2_token_introspect
    pre_introspect_count = introspect.call_count
    post_introspect_count = introspect.call_count
    assert pre_introspect_count == post_introspect_count
