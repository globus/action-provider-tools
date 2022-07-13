from unittest.mock import patch

import globus_sdk
import pytest

from globus_action_provider_tools import AuthState
from globus_action_provider_tools.authentication import TokenChecker

from .data import canned_responses


def pytest_addoption(parser):
    """
    Add CLI options to `pytest` to pass those options to the test cases.
    These options are used in `pytest_generate_tests`.
    """
    parser.addoption(
        "--live-api-calls",
        action="store_true",
        default=False,
        help="Don't mock out API calls during test run.",
    )


@pytest.fixture
def live_api(request):
    return request.config.getoption("--live-api-calls")


@pytest.fixture
def config():
    return dict(
        client_id=canned_responses.mock_client_id(),
        client_secret=canned_responses.mock_client_secret(),
        expected_scopes=(canned_responses.mock_scope(),),
        expected_audience=canned_responses.mock_expected_audience(),
    )


@pytest.fixture
@patch("globus_action_provider_tools.authentication.ConfidentialAppAuthClient")
def auth_state(MockAuthClient, config, monkeypatch) -> AuthState:
    # Mock the introspection first because that gets called as soon as we create
    # a TokenChecker
    client = MockAuthClient.return_value
    client.oauth2_token_introspect.return_value = (
        canned_responses.introspect_response()()
    )

    # Mock the dependent_tokens and list_groups functions bc they get used when
    # creating a GroupsClient
    client.oauth2_get_dependent_tokens.return_value = (
        canned_responses.dependent_token_response()()
    )
    monkeypatch.setattr(
        globus_sdk.GroupsClient, "get_my_groups", canned_responses.groups_response()
    )

    # Create a TokenChecker to be used to create a mocked auth_state object
    checker = TokenChecker(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        expected_scopes=config["expected_scopes"],
        expected_audience=config["expected_audience"],
    )
    auth_state = checker.check_token("NOT_A_TOKEN")

    # Reset the call count because check_token implicitly calls oauth2_token_introspect
    client.oauth2_token_introspect.call_count = 0

    # Mock out this AuthState instance's GroupClient
    # auth_state._groups_client = GroupsClient(authorizer=None)
    # auth_state._groups_client.list_groups = canned_responses.groups_response()
    return auth_state


@pytest.fixture
def duplicate_auth_state(auth_state: AuthState, config) -> AuthState:
    """This fixture provides an AuthState type object that has the same token value as the
    auth_state fixture above. This means that caching should make access to either of the
    returned auth_state objects return values from the same cache as the root key is the
    token value.

    """

    # Create a TokenChecker to be used to create a mocked auth_state object
    checker = TokenChecker(
        client_id=config["client_id"],
        client_secret=config["client_secret"],
        expected_scopes=config["expected_scopes"],
        expected_audience=config["expected_audience"],
    )
    dup_auth_state = checker.check_token(auth_state.bearer_token)
    # Set up the same mocked Auth client
    dup_auth_state.auth_client = auth_state.auth_client
    return dup_auth_state
