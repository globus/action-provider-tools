import json

import pytest

from globus_action_provider_tools.flask.exceptions import (
    ActionConflict,
    ActionNotFound,
    ActionProviderError,
    BadActionRequest,
    RequestValidationError,
    UnauthorizedRequest,
)


@pytest.mark.parametrize(
    "exc",
    [
        ActionConflict,
        ActionNotFound,
        ActionProviderError,
        BadActionRequest,
        RequestValidationError,
        UnauthorizedRequest,
    ],
)
def test_exceptions(exc):
    # Validate that all exceptions are JSON-able and contain status_code, error,
    # and description fields

    data = json.loads(exc().get_body())

    assert "code" in data
    assert data["code"] == exc.__name__
    assert "description" in data
