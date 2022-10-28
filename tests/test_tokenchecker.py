from typing import Dict
from unittest.mock import patch

from globus_action_provider_tools import TokenChecker

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
        _ = TokenChecker(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            expected_scopes=config["expected_scopes"],
        )
