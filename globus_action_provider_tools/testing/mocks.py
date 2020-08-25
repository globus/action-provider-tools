from typing import NamedTuple
from unittest.mock import PropertyMock, patch

from globus_sdk import ConfidentialAppAuthClient

from globus_action_provider_tools.data_types import AuthState


def mock_authstate():
    """
    Returns a dummy AuthState object with mocked out methods and properties.
    This is particularly useful for mocking out the TokenChecker.check_token
    function. Should only be used for testing because it avoids the need for
    supplying valid CLIENT_IDs, CLIENT_SECRETs, and TOKENs
    """

    def mock_check_authorization(*args, **kwargs):
        return True

    def mock_primary_identity(*args, **kwargs):
        return "urn:globus:auth:identity:00000000-0000-0000-0000-000000000000"

    def mock_introspect_token(*args, **kwargs):
        return None

    auth_client = ConfidentialAppAuthClient(None, None)
    auth_state = AuthState(auth_client, None, None)
    auth_state.check_authorization = mock_check_authorization
    auth_state.primary_identity = mock_primary_identity
    auth_state.introspect_token = mock_introspect_token
    auth_state.bearer_token = "MOCK_BEARER_TOKEN"

    # This is how you patch object @properties
    patch(
        "globus_action_provider_tools.authentication.AuthState.effective_identity",
        new_callable=PropertyMock,
        return_value="MOCK_USER",
    ).start()
    patch(
        "globus_action_provider_tools.authentication.AuthState.identities",
        new_callable=PropertyMock,
        return_value=frozenset("MOCK_USER"),
    ).start()

    return auth_state
