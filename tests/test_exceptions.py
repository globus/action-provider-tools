import json

import pytest

from globus_action_provider_tools.exceptions import (
    ActionConflict,
    ActionNotFound,
    ActionProviderError,
    BadActionRequest,
    UnauthorizedRequest,
)


@pytest.mark.parametrize(
    "exc",
    [
        ActionConflict,
        ActionNotFound,
        ActionProviderError,
        BadActionRequest,
        UnauthorizedRequest,
    ],
)
def test_exceptions(exc):
    # Validate that all exceptions are JSON-able and contain status_code, error,
    # and description fields

    with pytest.raises(exc) as exc_info:
        raise exc

    data = exc_info.value.get_response().get_data()
    data = json.loads(data)

    assert "error" in data
    assert data["error"] == exc.__name__
    assert "status_code" in data
    assert "description" in data
