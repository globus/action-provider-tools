from unittest import mock

import pytest

from globus_action_provider_tools.authentication import (
    InactiveTokenError,
    InvalidTokenScopesError,
)
from globus_action_provider_tools.errors import (
    AuthenticationError,
    UnverifiedAuthenticationError,
)
from globus_action_provider_tools.flask.helpers import FlaskAuthStateBuilder


@pytest.mark.parametrize(
    "authorization_header",
    (
        pytest.param(None, id="missing Authorization header"),
        pytest.param("", id="blank header value"),
        pytest.param("  ", id="whitespace header value"),
        pytest.param("A" * 100, id="no 'Bearer ' prefix"),
        pytest.param("Bearer " + "A" * 9, id="short token"),
        pytest.param("Bearer " + "A" * 2049, id="long token"),
    ),
)
def test_bogus_authorization_headers_are_rejected_without_io(authorization_header):
    # stub the Auth Client and scopes
    builder = FlaskAuthStateBuilder(mock.Mock(), [])

    headers = {}
    if authorization_header is not None:
        headers["Authorization"] = authorization_header

    mock_request_object = mock.Mock()
    mock_request_object.headers = headers

    # establish a mock which will raise an error if the code even *attempts*
    # to create an AuthState object
    # we should short-circuit before ever getting this far
    with mock.patch(
        "globus_action_provider_tools.authentication.AuthState",
        side_effect=RuntimeError("ON NO"),
    ):
        with pytest.raises(UnverifiedAuthenticationError):
            builder.build_from_request(request=mock_request_object)


@pytest.mark.parametrize(
    "underlying_error, expect_message",
    (
        (InactiveTokenError("foo"), "Token is invalid, expired, or revoked"),
        (
            InvalidTokenScopesError(frozenset(["foo"]), frozenset(["bar"])),
            "Token has invalid scopes",
        ),
    ),
)
def test_invalid_token_data_results_in_authn_errors(underlying_error, expect_message):
    # stub the Auth Client and scopes
    builder = FlaskAuthStateBuilder(mock.Mock(), [])

    mock_request_object = mock.Mock()
    mock_request_object.headers = {"Authorization": "Bearer AbcDefGhiJklmnop"}

    # mock in the underlying authentication related error
    with mock.patch(
        "globus_action_provider_tools.authentication.AuthState",
        side_effect=underlying_error,
    ):
        with pytest.raises(AuthenticationError, match=expect_message):
            builder.build_from_request(request=mock_request_object)
