from __future__ import annotations

import pathlib
import typing as t
from unittest import mock

import pytest
import responses
import yaml
from globus_sdk.testing import load_response, register_response_set
from globus_sdk.transport import RetryConfig

from globus_action_provider_tools.authentication import AuthState
from globus_action_provider_tools.client_factory import ClientFactory

from .data import canned_responses

try:
    import flask  # noqa: F401
except ModuleNotFoundError:
    collect_ignore = ["flask"]


class NoRetryClientFactory(ClientFactory):
    DEFAULT_RETRY_CONFIG = RetryConfig(max_retries=0)


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


class _RacyCacheProxy:
    """
    Wraps a TypedTTLCache so that every operation on it first runs
    `before_call`, simulating a concurrent thread's cache mutation
    happening in the gap between this call and whatever the caller
    does next.
    """

    def __init__(self, cache, before_call) -> None:
        self._cache = cache
        self._before_call = before_call

    def get(self, key):
        self._before_call(key)
        return self._cache.get(key)

    def __contains__(self, key):
        self._before_call(key)
        return key in self._cache

    def __getitem__(self, key):
        self._before_call(key)
        return self._cache[key]

    def __setitem__(self, key, value):
        self._before_call(key)
        self._cache[key] = value

    def __delitem__(self, key):
        self._before_call(key)
        del self._cache[key]

    def clear(self):
        self._cache.clear()


@pytest.fixture
def racy_evicting_cache(monkeypatch):
    """
    Simulate cache eviction race conditions.

    Code that interacts with a cache via separate check-then-use operations
    (for example, `if key in cache: token_data = cache[key]`) is vulnerable to
    a race condition known as "time-of-check to time-of-use" (TOCTOU): another
    thread can evict the entry in the gap between the check and the use.

    This fixture helps tests simulate a single concurrent thread winning
    that race exactly once.

    Usage:

        install(cache_attribute_name, key, evict_at_interaction=2)

    patches AuthState.<cache_attribute_name> so that, immediately before the
    `evict_at_interaction`-th operation performed against `key`, the entry
    is deleted once. Every other operation against `key` -- before or
    after -- is left alone and observes the real cache state.

    `evict_at_interaction` has no single correct value: it depends on how
    many legitimate cache operations the code under test performs against
    `key` before the operation you want to race, and callers must pass it
    explicitly. Tests should parametrize over a small range of values
    rather than hardcoding one, so the race is exercised regardless of
    exactly which call it lands on.
    """

    def install(cache_attribute_name, key, *, evict_at_interaction):
        real_cache = getattr(AuthState, cache_attribute_name)
        call_count = 0

        def before_call(k):
            nonlocal call_count
            if k != key:
                return
            call_count += 1
            if call_count == evict_at_interaction:
                real_cache._cache.pop(key, None)

        monkeypatch.setattr(
            AuthState, cache_attribute_name, _RacyCacheProxy(real_cache, before_call)
        )

    return install


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
