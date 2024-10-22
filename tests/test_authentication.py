from __future__ import annotations

import time
import typing as t
from unittest import mock

import globus_sdk
import pytest
from globus_sdk._testing import RegisteredResponse, load_response

from globus_action_provider_tools.authentication import (
    AuthState,
    InvalidTokenScopesError,
    identity_principal,
)


def get_auth_state_instance(expected_scopes: t.Iterable[str]) -> AuthState:
    client = globus_sdk.ConfidentialAppAuthClient(
        "bogus", "bogus", transport_params={"max_retries": 0}
    )
    return AuthState(
        auth_client=client,
        bearer_token="bogus",
        expected_scopes=frozenset(expected_scopes),
    )


@pytest.fixture(autouse=True)
def _clear_auth_state_cache():
    AuthState.dependent_tokens_cache.clear()
    AuthState.group_membership_cache.clear()
    AuthState.introspect_cache.clear()


@pytest.fixture
def auth_state(mocked_responses) -> AuthState:
    """Create an AuthState instance."""
    # note that expected-scope MUST match the fixture data
    return get_auth_state_instance(["expected-scope"])


def test_get_identities(auth_state, freeze_time):
    response = freeze_time(load_response("token-introspect", case="success"))
    assert len(auth_state.identities) == len(response.metadata["identities"])
    assert all(i.startswith("urn:globus:auth:identity") for i in auth_state.identities)


def test_get_groups(auth_state, freeze_time):
    load_response("token", case="success")
    freeze_time(load_response("token-introspect", case="success"))
    group_response = load_response("groups-my_groups", case="success")
    assert len(auth_state.groups) == len(group_response.metadata["group-ids"])
    assert all(g.startswith("urn:globus:groups:id:") for g in auth_state.groups)


def test_effective_identity(auth_state, freeze_time):
    response = freeze_time(load_response("token-introspect", case="success"))
    assert auth_state.effective_identity == identity_principal(
        response.metadata["effective-id"]
    )


def test_caching_identities(auth_state, freeze_time, mocked_responses):
    response = freeze_time(load_response("token-introspect", case="success"))
    num_test_calls = 10
    for _ in range(num_test_calls):
        assert len(auth_state.identities) == 6
        assert auth_state.effective_identity == identity_principal(
            response.metadata["effective-id"]
        )

    assert len(mocked_responses.calls) == 1


def test_caching_groups(auth_state, freeze_time, mocked_responses):
    load_response("token", case="success")
    freeze_time(load_response("token-introspect", case="success"))
    group_response = load_response("groups-my_groups", case="success")
    num_test_calls = 10
    for _ in range(num_test_calls):
        assert len(auth_state.groups) == len(group_response.metadata["group-ids"])

    assert len(mocked_responses.calls) == 2


def test_auth_state_caching_across_instances(auth_state, freeze_time, mocked_responses):
    response = freeze_time(load_response("token-introspect", case="success"))

    duplicate_auth_state = get_auth_state_instance(auth_state.expected_scopes)
    assert duplicate_auth_state is not auth_state

    assert len(auth_state.identities) == len(response.metadata["identities"])
    assert len(mocked_responses.calls) == 1
    # The second instance should see the cached value,
    # resulting in no additional HTTP calls.
    assert len(duplicate_auth_state.identities) == len(response.metadata["identities"])
    assert len(mocked_responses.calls) == 1


def test_invalid_grant_exception(auth_state):
    load_response("token-introspect", case="success")
    load_response("token", case="invalid-grant")
    assert auth_state.get_authorizer_for_scope("doesn't matter") is None


def test_dependent_token_callout_500_fails_dependent_authorization(auth_state):
    """
    On a 5xx response, getting an authorizer fails.

    FIXME: currently this simply emits 'None' -- in the future the error should propagate
    """
    RegisteredResponse(
        service="auth", path="/v2/oauth2/token", method="POST", status=500
    ).add()
    assert (
        auth_state.get_authorizer_for_scope(
            "urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships"
        )
        is None
    )


def test_dependent_token_callout_success_fixes_bad_cache(auth_state):
    """
    Populate the cache "incorrectly" and then "fix it" by asking for an authorizer
    and expecting the dependent token logic to appropriately redrive.
    """
    # the mock by_scopes value is a dict -- similar enough since it just needs to be
    # a mapping type -- which we populate for "foo"
    mock_response = mock.Mock()
    mock_response.by_scopes = {
        "foo_scope": {
            "expires_at_seconds": time.time() + 100,
            "access_token": "foo_AT",
            "refresh_token": "foo_RT",
        }
    }
    auth_state.dependent_tokens_cache[auth_state._dependent_token_cache_key] = (
        mock_response
    )

    # register a response for a different resource server -- 'bar'
    RegisteredResponse(
        service="auth",
        path="/v2/oauth2/token",
        method="POST",
        json=[
            {
                "resource_server": "bar",
                "scope": "bar_scope",
                "expires_at_seconds": time.time() + 100,
                "access_token": "bar_AT",
                "refresh_token": "bar_RT",
            }
        ],
    ).add()
    # now get the 'bar_scope' authorizer
    authorizer = auth_state.get_authorizer_for_scope("bar_scope")

    # it should be a refresh token authorizer and the cache should be updated
    assert isinstance(authorizer, globus_sdk.RefreshTokenAuthorizer)
    cache_value = auth_state.dependent_tokens_cache[
        auth_state._dependent_token_cache_key
    ]
    assert isinstance(cache_value, globus_sdk.OAuthDependentTokenResponse)
    assert "foo_scope" not in cache_value.by_scopes
    assert "bar_scope" in cache_value.by_scopes


def test_invalid_scopes_error():
    auth_state = get_auth_state_instance(["bad-scope"])
    load_response("token-introspect", case="success")
    with pytest.raises(InvalidTokenScopesError) as excinfo:
        auth_state.introspect_token()

    assert excinfo.value.expected_scopes == {"bad-scope"}
    assert excinfo.value.actual_scopes == {"expected-scope", "bonus-scope"}


def test_required_scopes_may_be_a_subset_of_token_scopes():
    """Verify that required scopes may be a subset of token scopes."""

    auth_state_instance = get_auth_state_instance(["expected-scope"])
    load_response("token-introspect", case="success")
    auth_state_instance.introspect_token()
