from unittest import mock

from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.data_types import AuthState
from globus_action_provider_tools.testing.mocks import mock_authstate


def test_create_mocked_tokenchecker():
    with mock.patch(
        "globus_action_provider_tools.authentication.TokenChecker.check_token",
        return_value=mock_authstate(),
    ):
        tc = TokenChecker(None, None, [None])

        assert tc is not None
        assert isinstance(tc, TokenChecker)


def test_mocked_tokenchecker_checks_token():
    with mock.patch(
        "globus_action_provider_tools.authentication.TokenChecker.check_token",
        return_value=mock_authstate(),
    ):
        tc = TokenChecker(None, None, [None])
        authstate = tc.check_token(None)

        assert authstate is not None
        assert isinstance(authstate, AuthState)
