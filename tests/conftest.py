from __future__ import annotations

import datetime
import pathlib
import typing as t
from unittest import mock

import freezegun
import pytest
import responses
import yaml
from globus_sdk._testing import RegisteredResponse, load_response, register_response_set

from globus_action_provider_tools.authentication import AuthState
from globus_action_provider_tools.client_factory import ClientFactory

from .data import canned_responses

try:
    import flask  # noqa: F401
except ModuleNotFoundError:
    collect_ignore = ["flask"]


class NoRetryClientFactory(ClientFactory):
    DEFAULT_AUTH_TRANSPORT_PARAMS = (("max_retries", 0),)
    DEFAULT_GROUPS_TRANSPORT_PARAMS = (("max_retries", 0),)


_NO_RETRY_FACTORY = NoRetryClientFactory()


@pytest.fixture
def config():
    return {
        "client_id": canned_responses.mock_client_id(),
        "client_secret": canned_responses.mock_client_secret(),
        "expected_scopes": (canned_responses.mock_scope(),),
    }


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
def introspect_success_response(mocked_responses):
    return load_response("token-introspect", case="success")


@pytest.fixture
def dependent_token_success_response(mocked_responses):
    return load_response("token", case="success")


@pytest.fixture
def groups_success_response(mocked_responses):
    return load_response("groups-my_groups", case="success")


@pytest.fixture
def get_auth_state_instance() -> t.Callable[..., AuthState]:
    def _func(
        expected_scopes: t.Iterable[str],
        client_factory: ClientFactory = _NO_RETRY_FACTORY,
    ) -> AuthState:
        client = client_factory.make_confidential_app_auth_client("bogus", "bogus")
        return AuthState(
            auth_client=client,
            bearer_token="bogus",
            expected_scopes=frozenset(expected_scopes),
            client_factory=client_factory,
        )

    return _func


@pytest.fixture(autouse=True)
def _clear_auth_state_cache():
    AuthState.dependent_tokens_cache.clear()
    AuthState.group_membership_cache.clear()
    AuthState.introspect_cache.clear()


@pytest.fixture
def auth_state(
    mocked_responses,
    get_auth_state_instance: t.Callable[..., AuthState],
    introspect_success_response,
    dependent_token_success_response,
    groups_success_response,
) -> AuthState:
    """Create an AuthState instance."""
    # note that expected-scope MUST match the fixture data
    return get_auth_state_instance(["expected-scope"])


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
