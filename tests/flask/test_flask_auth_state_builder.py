from unittest import mock

import pytest

from globus_action_provider_tools.errors import UnverifiedAuthenticationError
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