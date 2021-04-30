import inspect
import json
from enum import Enum
from functools import partial
from typing import Any, Callable, Dict, Iterable, Set, Type

from flask import Request, current_app, jsonify
from jsonschema.validators import Draft7Validator
from pydantic import BaseModel, ValidationError

from globus_action_provider_tools.authentication import AuthState, TokenChecker
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionRequest,
    ActionStatus,
)
from globus_action_provider_tools.errors import AuthenticationError
from globus_action_provider_tools.flask.exceptions import (
    ActionProviderError,
    ActionProviderToolsException,
    BadActionRequest,
    UnauthorizedRequest,
)
from globus_action_provider_tools.flask.types import ActionStatusReturn, ViewReturn
from globus_action_provider_tools.validation import validate_data

ActionInputValidatorType = Callable[[Dict[str, Any]], None]


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

    # If a component in the toolkit throw's an unhandled AuthenticationError,
    # replace it with a Flask-based response
    if isinstance(exc, AuthenticationError):
        return UnauthorizedRequest()  # type: ignore

    current_app.logger.exception(str(exc))
    # Handle unexpected Exceptions in a somewhat predictable way
    resp = {
        "code": ActionProviderError.__name__,
        "description": f"Internal Server Error",
    }
    return jsonify(resp), 500


def validate_input(
    request_json: Dict[str, Any], input_body_validator: ActionInputValidatorType
) -> ActionRequest:
    """
    Ensures the incoming request conforms to the ActionRequest schema and
    the user-defined ActionProvider input schema.
    """
    try:
        action_request = ActionRequest(**request_json)
    except ValidationError as ve:
        raise BadActionRequest(ve.errors())

    try:
        input_body_validator(action_request.body)
    except BadActionRequest as err:
        raise

    return action_request


def get_input_body_validator(
    provider_description: ActionProviderDescription,
) -> ActionInputValidatorType:
    """
    Inspects the value of the provider_description's input_schema to
    determine if it's a str, dict, or pydantic Model to figure out which
    validation function to use.

    If the input_schema is a str or dict, raw json_schema validation will
    be used. An jsonschema DraftValidator is created and applied to
    json_schema_input_validation creating a new partial which can be called by
    simply supplying the input to validate.

    If the input_schema is a pydantic BaseModel subclass, we apply the
    input_schema to pydantic_input_validation creating a new partial which can
    be called by simply supplying the input to validate.
    """
    input_schema = provider_description.input_schema

    if isinstance(input_schema, str):
        input_schema = json.loads(input_schema)
    elif isinstance(input_schema, dict):
        pass
    elif inspect.isclass(input_schema) and issubclass(input_schema, BaseModel):
        return partial(pydantic_input_validation, validator=input_schema)
    else:
        raise ActionProviderError(
            "Unable to determine input schema from ActionProviderDescription"
        )

    return partial(
        json_schema_input_validation, validator=Draft7Validator(input_schema)
    )


def json_schema_input_validation(
    action_input: Dict[str, Any], validator: Draft7Validator
) -> None:
    """
    Use a created JSON Validator to verify the input body of an incoming
    request conforms to the defined JSON schema. In the event that the
    validation reports any errors, a BadActionRequest exception gets raised.
    """
    result = validate_data(action_input, validator)
    if result.errors:
        raise BadActionRequest(result.errors)


def pydantic_input_validation(
    action_input: Dict[str, Any], validator: Type[BaseModel]
) -> None:
    """
    Validate input using the pydantic model itself. Raises a BadActionRequest
    exception if the input is incorrect.
    """
    try:
        validator(**action_input)
    except ValidationError as ve:
        raise BadActionRequest(ve.errors())
