import random
from typing import Dict
from unittest.mock import patch

import dogpile
import pytest

from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.caching import dogpile_cache

from .data import canned_responses


@patch("globus_action_provider_tools.authentication.ConfidentialAppAuthClient")
def test_create_multiple_tokencheckers(MockAuthClient, config: Dict):
    # Mock the introspection first because that gets called as soon as we create
    # a TokenChecker
    client = MockAuthClient.return_value
    client.oauth2_token_introspect.return_value = (
        canned_responses.introspect_response()()
    )

    MAX_TOKEN_CHECKERS = 3
    for _ in range(MAX_TOKEN_CHECKERS):
        try:
            _ = TokenChecker(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
                expected_scopes=config["expected_scopes"],
            )
        except dogpile.cache.exception.RegionAlreadyConfigured as err:
            pytest.fail(f"{err}")


@patch("globus_action_provider_tools.authentication.ConfidentialAppAuthClient")
def test_custom_tokenchecker(MockAuthClient, config: Dict):
    # Mock the introspection first because that gets called as soon as we create
    # a TokenChecker
    client = MockAuthClient.return_value
    client.oauth2_token_introspect.return_value = (
        canned_responses.introspect_response()()
    )

    custom_config = {"timeout": random.randint(0, 1000)}
    config.update(custom_config)
    try:
        _ = TokenChecker(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            expected_scopes=config["expected_scopes"],
            cache_config=config,
        )
    except Exception as err:
        pytest.fail(f"{err}")

    assert dogpile_cache.__dict__["expiration_time"] == custom_config["timeout"]
