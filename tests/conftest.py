from __future__ import annotations

import datetime
import pathlib
import typing as t
from unittest import mock

import freezegun
import globus_sdk
import pytest
import responses
import yaml
from globus_sdk._testing import RegisteredResponse, register_response_set

from globus_action_provider_tools.authentication import AuthState, AuthStateBuilder

from .data import canned_responses

try:
    import flask

    assert flask
except ModuleNotFoundError:
    collect_ignore = ["flask"]


@pytest.fixture
def config():
    return {
        "client_id": canned_responses.mock_client_id(),
        "client_secret": canned_responses.mock_client_secret(),
        "expected_scopes": (canned_responses.mock_scope(),),
    }


@pytest.fixture
@mock.patch("globus_sdk.ConfidentialAppAuthClient")
def auth_state(MockAuthClient, config, monkeypatch) -> AuthState:
    # FIXME: the comment below is a lie, assess and figure out what is being said
    #
    # Mock the introspection first because that gets called as soon as we create
    # an AuthStateBuilder
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

    # Create an AuthStateBuilder to be used to create a mocked auth_state object
    builder = AuthStateBuilder(client, expected_scopes=config["expected_scopes"])
    auth_state = builder.build("NOT_A_TOKEN")

    # Reset the call count because check_token implicitly calls oauth2_token_introspect
    client.oauth2_token_introspect.call_count = 0

    # Mock out this AuthState instance's GroupClient
    # auth_state._groups_client = GroupsClient(authorizer=None)
    # auth_state._groups_client.list_groups = canned_responses.groups_response()
    return auth_state


@pytest.fixture
def apt_blueprint_noauth(auth_state):
    """
    A fixture function which will mock an ActionProviderBlueprint instance's
    AuthStateBuilder.
    """

    def _apt_blueprint_noauth(aptb):
        # Manually remove the function that creates the internal state_builder
        for f in aptb.deferred_functions:
            if f.__name__ == "_create_state_builder":
                aptb.deferred_functions.remove(f)

        # Use a mocked auth state builder internally
        aptb.state_builder = mock.Mock()
        aptb.state_builder.build.return_value = auth_state
        aptb.state_builder.build_from_request.return_value = auth_state

    return _apt_blueprint_noauth


@pytest.fixture
def flask_helpers_noauth(auth_state):
    with mock.patch(
        "globus_action_provider_tools.flask.api_helpers.TokenChecker.check_token",
        return_value=auth_state,
    ):
        yield


@pytest.fixture(scope="session", autouse=True)
def register_api_fixtures():
    for yaml_file in (pathlib.Path(__file__).parent / "api-fixtures").rglob("*.yaml"):
        response_set = yaml.safe_load(yaml_file.read_text())
        register_response_set(yaml_file.stem, response_set)


@pytest.fixture(autouse=True)
def mocked_responses() -> responses.RequestsMock:
    """Mock all requests.

    The default `responses.mock` object is returned,
    which allows tests to access various properties of the mock.
    For example, they might check the number of intercepted `.calls`.
    """

    with responses.mock:
        yield responses.mock


@pytest.fixture
def freeze_time() -> (
    t.Generator[t.Callable[[RegisteredResponse], RegisteredResponse], None, None]
):
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
            assert frozen_time is None, "You can't freeze time twice!"
            frozen_time = freezegun.freeze_time(instant)
            frozen_time.start()
        return response

    try:
        yield freezer
    finally:
        # Unfreeze time, if needed.
        if frozen_time is not None:
            frozen_time.stop()
