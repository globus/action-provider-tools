from __future__ import annotations

import datetime
import pathlib
import typing as t

import freezegun
import globus_sdk
import pytest
import responses
import yaml
from globus_sdk._testing import (
    RegisteredResponse,
    load_response_set,
    register_response_set,
)

from globus_action_provider_tools.authentication import AuthState, AuthStateFactory

from .data import canned_responses


@pytest.fixture
def config():
    return dict(
        client_id=canned_responses.mock_client_id(),
        client_secret=canned_responses.mock_client_secret(),
        expected_scopes=(canned_responses.mock_scope(),),
        expected_audience=canned_responses.mock_expected_audience(),
    )


@pytest.fixture(scope="session", autouse=True)
def register_api_fixtures():
    canned_responses.register_responses()
    for yaml_file in (pathlib.Path(__file__).parent / "api-fixtures").rglob("*.yaml"):
        response_set = yaml.safe_load(yaml_file.read_text())
        register_response_set(yaml_file.stem, response_set)


@pytest.fixture(autouse=True)
def mocked_responses():
    """Mock all requests.

    The default `responses.mock` object is returned,
    which allows tests to access various properties of the mock.
    For example, they might check the number of intercepted `.calls`.
    """
    responses.start()

    yield

    responses.stop()
    responses.reset()


@pytest.fixture
def auth_state(mocked_responses, config, monkeypatch) -> AuthState:
    load_response_set("ap-tools-canned-responses")

    dummy_client = globus_sdk.ConfidentialAppAuthClient(
        "foo_client_id", "bar_client_secret"
    )
    factory: AuthStateFactory[AuthState] = AuthStateFactory(auth_client=dummy_client)
    auth_state = factory.make_state("DummyToken")

    return auth_state


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
