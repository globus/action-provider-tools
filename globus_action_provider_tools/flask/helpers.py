from enum import Enum
from typing import Iterable, Set

from flask import Request, jsonify
from werkzeug.exceptions import HTTPException

from globus_action_provider_tools.authentication import AuthState, TokenChecker
from globus_action_provider_tools.data_types import ActionStatus
from globus_action_provider_tools.exceptions import (
    ActionProviderError,
    ActionProviderToolsException,
)
from globus_action_provider_tools.flask.types import ActionStatusReturn, ViewReturn


def parse_query_args(
    request: Request,
    *,
    arg_name: str,
    default_value: str = "",
    valid_vals: Set[str] = None,
) -> Set[str]:
    """
    Helper function to parse a query arg "arg_name" and return a validated
    (according to the values supplied in "valid_vals"), usable set of
    values (which defaults to "default_value").

    Note that this helper expects to be provided a Flask request to inspect
    query parameters.
    """
    param_val = request.args.get(arg_name, default_value)

    # A query param name with no value returns empty string even with default value
    if param_val == "":
        param_val = default_value

    # Split in case there's a comma seperated query param value
    param_vals = set(param_val.split(","))

    # Remove invalid data from query params
    if valid_vals is not None:
        param_vals = {pv.casefold() for pv in param_vals if pv.casefold() in valid_vals}

    # If after processing, our param vals are empty, simply return the default
    if not param_vals:
        param_vals = {default_value}
    return param_vals


def query_args_to_enum(args: Iterable[str], enum_class: Enum):
    """
    Helper function to return an arg value as a valid value for an Enum
    """
    new_args = set()
    for arg in args:
        try:
            new_arg = enum_class[arg]  # type: ignore
        except KeyError:
            try:
                new_arg = enum_class[arg.upper()]  # type: ignore
            except KeyError:
                continue
        new_args.add(new_arg)

    return new_args


def action_status_return_to_view_return(
    status: ActionStatusReturn, default_status_code: int
) -> ViewReturn:
    """
    Helper function to return a ActionStatusReturn object as a valid Flask
    response.
    """
    if isinstance(status, ActionStatus):
        status_code = default_status_code
    elif isinstance(status, tuple):
        status, status_code = status
    return jsonify(status), status_code


def check_token(request: Request, checker: TokenChecker) -> AuthState:
    """
    Parses a Flask request to extract its bearer token.
    """
    access_token = request.headers.get("Authorization", "").strip().lstrip("Bearer ")
    auth_state = checker.check_token(access_token)
    return auth_state


def blueprint_error_handler(exc: Exception) -> ViewReturn:
    # ActionProviderToolsException is the base class for HTTP-based exceptions,
    # return those directly
    if isinstance(exc, ActionProviderToolsException):
        return exc  # type: ignore

    # Handle unexpected Exceptions in a somewhat predictable way
    return (
        jsonify(
            {
                "error": ActionProviderError.__name__,
                "description": f"Unexpected Error: {str(exc)}",
                "status_code": 500,
            }
        ),
        500,
    )
