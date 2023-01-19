from unittest.mock import Mock

from globus_action_provider_tools.authentication import AuthState, AuthStateFactory


def mock_authstate(*args, **kwargs):
    """
    Returns a dummy AuthState object with mocked out methods and properties.
    This is particularly useful for mocking out the TokenChecker.check_token
    function. Should only be used for testing because it avoids the need for
    supplying valid CLIENT_IDs, CLIENT_SECRETs, and TOKENs
    """
    # auth_client = ConfidentialAppAuthClient(None, None)
    auth_state = Mock(spec=AuthState, name="MockedAPTAuthState")

    auth_state.token = "MOCK_BEARER_TOKEN"
    auth_state.effective_identity = (
        "urn:globus:auth:identity:00000000-0000-0000-0000-000000000000"
    )
    auth_state.identities = frozenset([auth_state.effective_identity])

    # Mock other functions that get called
    auth_state.check_authorization.return_value = True

    return auth_state


def mock_auth_state_factory(*args, **kwargs):
    """
    Returns a dummy TokenChecker object with a mocked out check_token method.
    In turn, this mock can only produce mocked_authstates.
    """
    factory = Mock(spec=AuthStateFactory, name="MockedAPAuthStateFactory")
    factory.make_state.return_value = mock_authstate()
    return factory
