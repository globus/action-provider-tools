import pytest
from globus_sdk._testing import RegisteredResponse

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


def test_freeze_time_two_freezes(freeze_time):
    """Verify that it's impossible to freeze time twice.

    Did you find this test because you added new tests, got an error,
    tried changing some code, and are now seeing this test fail?
    Great! You've come to the right place.

    If you need to freeze time twice, it may be easier to align the time
    in your mocked API response with the time in an existing mocked API response.
    You can do this by changing the time values in your new API response.
    Do not add `metadata["freezegun"]` in your new API response.

    If you *really* need to freeze time twice, go ahead and do so.
    You can change or remove this test completely,
    but please ensure that you are testing the changes you introduced
    in the `freeze_time` fixture (if any).
    """

    response = RegisteredResponse(
        path="does/not/matter",
        metadata={"freezegun": 1000},
    )
    freeze_time(response)
    with pytest.raises(AssertionError):
        freeze_time(response)
