from __future__ import annotations

import time
from unittest import mock

import globus_sdk
import pytest
from globus_sdk._testing import RegisteredResponse, get_response_set

from globus_action_provider_tools.authentication import (
    InvalidTokenScopesError,
    identity_principal,
)
from globus_action_provider_tools.client_factory import ClientFactory


class FastRetryClientFactory(ClientFactory):
    DEFAULT_AUTH_TRANSPORT_PARAMS = (("max_sleep", 0), ("max_retries", 1))
    DEFAULT_GROUPS_TRANSPORT_PARAMS = (("max_sleep", 0), ("max_retries", 1))


def test_get_identities(auth_state, introspect_success_response):
    assert len(auth_state.identities) == len(
        introspect_success_response.metadata["identities"]
    )
    assert all(i.startswith("urn:globus:auth:identity") for i in auth_state.identities)


def test_get_groups(auth_state, groups_success_response):
    assert len(auth_state.groups) == len(groups_success_response.metadata["group-ids"])
    assert all(g.startswith("urn:globus:groups:id:") for g in auth_state.groups)


def test_effective_identity(auth_state, introspect_success_response):
    assert auth_state.effective_identity == identity_principal(
        introspect_success_response.metadata["effective-id"]
    )


def test_caching_identities(auth_state, introspect_success_response, mocked_responses):
    num_test_calls = 10
    for _ in range(num_test_calls):
        assert len(auth_state.identities) == 7
        assert auth_state.effective_identity == identity_principal(
            introspect_success_response.metadata["effective-id"]
        )

    assert len(mocked_responses.calls) == 1


def test_caching_groups(auth_state, mocked_responses, groups_success_response):
    num_test_calls = 10
    for _ in range(num_test_calls):
        assert len(auth_state.groups) == len(
            groups_success_response.metadata["group-ids"]
        )

    # 3 calls no matter how many times the loop runs:
    # - introspect
    # - dependent token lookup
    # - groups callout
    assert len(mocked_responses.calls) == 3


def test_auth_state_caching_across_instances(
    get_auth_state_instance,
    auth_state,
    freeze_time,
    mocked_responses,
    introspect_success_response,
):
    duplicate_auth_state = get_auth_state_instance(auth_state.expected_scopes)
    assert duplicate_auth_state is not auth_state

    assert len(auth_state.identities) == len(
        introspect_success_response.metadata["identities"]
    )
    assert len(mocked_responses.calls) == 1
    # The second instance should see the cached value,
    # resulting in no additional HTTP calls.
    assert len(duplicate_auth_state.identities) == len(
        introspect_success_response.metadata["identities"]
    )
    assert len(mocked_responses.calls) == 1


def test_deprecation_warning_on_required_authorizer_expiration_time(auth_state):
    with pytest.warns(
        DeprecationWarning,
        match="`required_authorizer_expiration_time` has no effect and will be removed",
    ):
        auth_state.get_authorizer_for_scope(
            "urn:globus:auth:scope:groups.api.globus.org:view_my_groups_and_memberships",
            required_authorizer_expiration_time=60,
        )


def test_invalid_grant_exception(auth_state, introspect_success_response):
    get_response_set("token").lookup("invalid-grant").replace()
    with pytest.raises(globus_sdk.GlobusAPIError):
        auth_state.get_authorizer_for_scope("doesn't matter")


@pytest.mark.parametrize(
    "statuses, succeeds",
    (
        pytest.param((500, 200), True, id="500-200-succeeds"),
        pytest.param((500, 500, 200), False, id="500-500-200-fails"),
    ),
)
def test_dependent_token_callout_500_retry_behavior(
    caplog, introspect_success_response, get_auth_state_instance, statuses, succeeds
):
    """
    Test the behavior of 500s and retries using the FastRetryClientFactory defined above.

    On a 5xx response followed by a 200, getting an authorizer succeeds.
    (Default configuration)

    On two 5xx responses followed by a 200, getting an authorizer fails.
    (Default configuration)
    """
    auth_state = get_auth_state_instance(
        ["expected-scope"], client_factory=FastRetryClientFactory()
    )
    body_for_200s = [
        {
            "access_token": "oompa-loompa-doompa-de-access-token",
            "resource_server": "wonka-chocolates.api.globus.org",
            "scope": "golden-ticket",
            "expires_in": 3600,
            "refresh_token": None,
            "token_type": "bearer",
        },
    ]

    for status in statuses:
        if status == 200:
            body = body_for_200s
        else:
            body = {}
        RegisteredResponse(
            service="auth",
            path="/v2/oauth2/token",
            method="POST",
            status=status,
            json=body,
        ).add()

    if succeeds:
        authorizer = auth_state.get_authorizer_for_scope("golden-ticket")
        assert isinstance(authorizer, globus_sdk.AccessTokenAuthorizer)
    else:
        with pytest.raises(globus_sdk.GlobusAPIError) as excinfo:
            auth_state.get_authorizer_for_scope("golden-ticket")
        error = excinfo.value
        assert error.http_status == 500


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
            }
        ],
    ).replace()
    # now get the 'bar_scope' authorizer
    authorizer = auth_state.get_authorizer_for_scope("bar_scope")

    # it should be an access token authorizer and the cache should be updated
    assert isinstance(authorizer, globus_sdk.AccessTokenAuthorizer)
    cache_value = auth_state.dependent_tokens_cache[
        auth_state._dependent_token_cache_key
    ]
    assert isinstance(cache_value, globus_sdk.OAuthDependentTokenResponse)
    assert "foo_scope" not in cache_value.by_scopes
    assert "bar_scope" in cache_value.by_scopes


def test_invalid_scopes_error(get_auth_state_instance, introspect_success_response):
    with pytest.raises(InvalidTokenScopesError) as excinfo:
        get_auth_state_instance(["bad-scope"])

    assert excinfo.value.expected_scopes == {"bad-scope"}
    assert excinfo.value.actual_scopes == {"expected-scope", "bonus-scope"}


def test_required_scopes_may_be_a_subset_of_token_scopes(
    get_auth_state_instance, introspect_success_response
):
    """Verify that required scopes may be a subset of token scopes."""
    auth_state = get_auth_state_instance(["expected-scope"])

    assert auth_state.expected_scopes == frozenset(["expected-scope"])

    assert "expected-scope" in introspect_success_response.metadata["scope"]
    assert "expected-scope" != introspect_success_response.metadata["scope"]


def test_no_groups_client_is_constructed_when_cache_is_warm(auth_state):
    """
    Confirm that if the group cache is warm, then the AuthState will refer to it without
    even trying to collect credentials to callout to groups.
    """
    get_response_set("groups-my_groups").lookup("failure").replace()

    # put a mock in place so that we can see whether or not a client was built
    auth_state._get_groups_client = mock.Mock()

    # write a value directly into the cache
    auth_state.group_membership_cache[auth_state._token_hash] = frozenset()

    # now, fetch the groups property -- it should populate properly with an empty set
    # even though there would be an error if we called out to groups
    assert len(auth_state.groups) == 0

    # finally, confirm via our mock that there was no attempt to instantiate a
    # groups client
    auth_state._get_groups_client.assert_not_called()
