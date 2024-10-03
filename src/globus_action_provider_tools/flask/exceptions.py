"""
This module contains JSON-able HTTP exceptions based off Werkzeug's
HTTPException class. These custom exceptions produce a JSON response containing
error name, http status code, and a description of the issue.

These exceptions can be raised with a default message directly from Werkzeug:
    raise ActionProviderToolsException

or a custom error message can be supplied:
    raise ActionNotFound("User unauthorized to run Action")
"""

import json
import typing as t

from werkzeug.exceptions import (
    BadRequest,
    Conflict,
    HTTPException,
    InternalServerError,
    NotFound,
    Unauthorized,
    UnprocessableEntity,
)

JSONType = t.Union[str, int, float, bool, None, t.Dict[str, t.Any], t.List[t.Any]]


class ActionProviderToolsException(HTTPException):
    @property
    def name(self):
        return type(self).__name__

    def get_body(self, *args):
        return json.dumps(
            {
                "code": self.name,
                "description": self.description,
            }
        )

    def get_headers(self, *args):
        return [("Content-Type", "application/json")]


class ActionNotFound(ActionProviderToolsException, NotFound):
    pass


class BadActionRequest(BadRequest, ActionProviderToolsException):
    pass


class RequestValidationError(UnprocessableEntity, BadActionRequest):
    # TODO: This inherits from BadActionRequest to avoid breaking
    # downstream code that expects to catch BadActionRequest when an error occurs
    # during validation. Remove this inheritance in a future release.
    pass


class ActionConflict(ActionProviderToolsException, Conflict):
    pass


class UnauthorizedRequest(ActionProviderToolsException, Unauthorized):
    description = (
        "The server could not verify that you are authorized "
        "to access the URL requested."
    )


class ActionProviderError(ActionProviderToolsException, InternalServerError):
    pass
