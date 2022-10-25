from __future__ import annotations

import datetime
import pathlib
import typing as t
from unittest.mock import patch

import freezegun
import globus_sdk
import pytest
import responses as responses_module
import yaml
from globus_sdk._testing import RegisteredResponse, register_response_set

from globus_action_provider_tools.authentication import AuthState, TokenChecker

from .data import canned_responses


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


@pytest.fixture(scope="session", autouse=True)
def register_api_fixtures():
    for yaml_file in (pathlib.Path(__file__).parent / "api-fixtures").rglob("*.yaml"):
        response_set = yaml.safe_load(yaml_file.read_text())
        register_response_set(yaml_file.stem, response_set)


@pytest.fixture(autouse=True)
def responses() -> responses_module.RequestsMock:
    """Mock all requests.

    The default `responses.mock` object is returned,
    which allows tests to access various properties of the mock.
    For example, they might check the number of intercepted `.calls`.
    """

    responses_module.reset()
    responses_module.start()
    try:
        yield responses_module.mock
    finally:
        responses_module.stop()


@pytest.fixture
def freeze_time() -> t.Generator[
    t.Callable[[RegisteredResponse], RegisteredResponse], None, None
]:
    """Inspect a Globus SDK RegisteredResponse object and freeze time if needed.

    Some responses may only be valid within a specific time range
    (for example, a token may only be valid within a specific time period).
    This fixture creates a function that will look for a "freezegun" key
    in the Response metadata. If found, time will be frozen at that value.
    """

    frozen_time: t.Optional[freezegun.freeze_time] = None

    def freezer(response: RegisteredResponse) -> RegisteredResponse:
        """Freeze time based on a "freezegun" key (if any) in the response metadata."""

        if "freezegun" in response.metadata:
            instant = datetime.datetime.utcfromtimestamp(response.metadata["freezegun"])
            # Update `frozen_time` in the outer scope.
            nonlocal frozen_time
            frozen_time = freezegun.freeze_time(instant)
            frozen_time.start()
        return response

    try:
        yield freezer
    finally:
        # Unfreeze time, if needed.
        if frozen_time is not None:
            frozen_time.stop()
