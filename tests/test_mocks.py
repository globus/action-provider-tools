import pytest

from globus_action_provider_tools import AuthState, TokenChecker
from globus_action_provider_tools.testing.mocks import mock_authstate, mock_tokenchecker


def test_create_mocked_tokenchecker():
    tc = mock_tokenchecker("", "not_a_secret", bogus_kwarg="sure")

    assert tc is not None
    assert isinstance(tc, TokenChecker)


def test_mocked_tokenchecker_checks_token():
    auth = mock_tokenchecker().check_token(None)

    assert auth is not None
    assert isinstance(auth, AuthState)


def test_tokenchecker_is_specced():
    tc = mock_tokenchecker()
    with pytest.raises(AttributeError):
        tc.not_a_valid_method()


def test_create_mocked_authstate():
    auth = mock_authstate("", "not_a_secret", bogus_kwarg="sure")

    assert auth is not None
    assert isinstance(auth, AuthState)


def test_authstate_is_specced():
    authstate = mock_authstate()
    with pytest.raises(AttributeError):
        authstate.not_a_valid_method()


def test_mocked_tokenchecker_creates_mocked_authstate():
    assert (
        mock_authstate().effective_identity
        == mock_tokenchecker().check_token().effective_identity
    )
