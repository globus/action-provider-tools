from unittest.mock import Mock

from globus_sdk import ConfidentialAppAuthClient

from globus_action_provider_tools.authentication import AuthState, TokenChecker


def mock_authstate(*args, **kwargs):
    """
    Returns a dummy AuthState object with mocked out methods and properties.
    This is particularly useful for mocking out the TokenChecker.check_token
    function. Should only be used for testing because it avoids the need for
    supplying valid CLIENT_IDs, CLIENT_SECRETs, and TOKENs
    """
    # auth_client = ConfidentialAppAuthClient(None, None)
    auth_state = Mock(spec=AuthState, name="MockedAPTAuthState")

    # Spec wont create instance variables created in __init__, so manually
    # create bearer_token
    auth_state.bearer_token = "MOCK_BEARER_TOKEN"

    # Set property mocks
    auth_state.effective_identity = (
        "urn:globus:auth:identity:00000000-0000-0000-0000-000000000000"
    )
    auth_state.identities = frozenset([auth_state.effective_identity])

    # Mock other functions that get called
    auth_state.check_authorization.return_value = True
    auth_state.introspect_token.return_value = None

    return auth_state


def mock_tokenchecker(*args, **kwargs):
    """
    Returns a dummy TokenChecker object with a mocked out check_token method.
    In turn, this mock can only produce mocked_authstates.
    """
    tokenchecker = Mock(spec=TokenChecker, name="MockedAPTTokenChecker")
    tokenchecker.check_token.return_value = mock_authstate()
    return tokenchecker
