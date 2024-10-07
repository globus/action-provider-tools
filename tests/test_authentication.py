from __future__ import annotations

import typing as t

import globus_sdk
import pytest
from globus_sdk._testing import load_response

from globus_action_provider_tools.authentication import AuthState, identity_principal


def get_auth_state_instance(expected_scopes: t.Iterable[str]) -> AuthState:
    return AuthState(
        auth_client=globus_sdk.ConfidentialAppAuthClient("bogus", "bogus"),
        bearer_token="bogus",
        expected_scopes=expected_scopes,
    )


@pytest.fixture
def auth_state(mocked_responses) -> AuthState:
    """Create an AuthState instance.

    AuthState compares its `expected_scopes` and `expected_audience` values
    against the values present in an API request and will fail if they don't match.
    Unfortunately, this currently means that these values are duplicated
    in the API fixture .yaml files and here.
    """

    AuthState.dependent_tokens_cache.clear()
    AuthState.group_membership_cache.clear()
    AuthState.introspect_cache.clear()
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
