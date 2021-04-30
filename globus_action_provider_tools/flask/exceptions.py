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
)

JSONType = t.Union[str, int, float, bool, None, t.Dict[str, t.Any], t.List[t.Any]]


class ActionProviderToolsException(HTTPException):
    # This is only required to update allow mypy to recognize the description
    # can be any JSON-able structure
    def __init__(self, description: t.Optional[JSONType] = None, *args, **kwargs):
        if description is not None:
            description = json.dumps(description)
        super().__init__(description, *args, **kwargs)

    @property
    def name(self):
        return type(self).__name__

    def get_body(self, *args):
        return json.dumps(
            {
                "code": self.name,
                "description": self.get_description(),
            }
        )

    def get_headers(self, *args):
        return [("Content-Type", "application/json")]

    def get_description(self, *args):
        try:
            return json.loads(self.description)
        except json.decoder.JSONDecodeError:
            return self.description


class ActionNotFound(ActionProviderToolsException, NotFound):
    pass


class BadActionRequest(BadRequest, ActionProviderToolsException):
    pass


class ActionConflict(ActionProviderToolsException, Conflict):
    pass


class UnauthorizedRequest(ActionProviderToolsException, Unauthorized):
    pass


class ActionProviderError(ActionProviderToolsException, InternalServerError):
    pass
