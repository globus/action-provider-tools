from __future__ import annotations

import inspect
import json
import typing as t
from enum import Enum
from functools import partial
from typing import Any, Callable, Dict, Iterable

import flask
import jsonschema
from flask import Request, current_app, jsonify
from pydantic import BaseModel, ValidationError

from globus_action_provider_tools.authentication import AuthState, AuthStateBuilder
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionProviderJsonEncoder,
    ActionRequest,
    ActionStatus,
    RequestObject,
    convert_to_json,
)
from globus_action_provider_tools.errors import (
    AuthenticationError,
    UnverifiedAuthenticationError,
)
from globus_action_provider_tools.flask.config import (
    DEFAULT_CONFIG,
    ActionProviderConfig,
)
from globus_action_provider_tools.flask.exceptions import (
    ActionProviderError,
    ActionProviderToolsException,
    RequestValidationError,
    UnauthorizedRequest,
)
from globus_action_provider_tools.flask.types import ActionCallbackReturn, ViewReturn
from globus_action_provider_tools.validation import (
    format_validation_error,
    validate_data,
)

if t.TYPE_CHECKING:
    from pydantic.error_wrappers import Loc


ActionInputValidatorType = Callable[[Dict[str, Any]], None]


class FlaskAuthStateBuilder(AuthStateBuilder):
    """
    A customized AuthStateBuilder which can handle a flask.Request object
    as its input.
    """

    def build_from_request(self, *, request: Request | None = None) -> AuthState:
        """
        Build the ``AuthState`` from the ``Authorization`` header provided.

        :param request: The flask request object to process. Defaults to the request
            object found in the current app context.
        """
        if request is None:
            request = flask.request
        access_token = request.headers.get("Authorization")
        if access_token is None:
            raise UnverifiedAuthenticationError("No Authorization header received")
        if not access_token.startswith("Bearer "):
            raise UnverifiedAuthenticationError(
                "No Bearer token in Authorization header"
            )
        access_token = access_token[len("Bearer ") :].strip()
        if not 10 <= len(access_token) <= 2048:
            raise UnverifiedAuthenticationError("Bearer token length is unexpected")

        return super().build(access_token)


def parse_query_args(
    request: Request,
    *,
    arg_name: str,
    default_value: str = "",
    valid_vals: set[str] | None = None,
) -> set[str]:
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

    # Split in case there's a comma separated query param value
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
    status: ActionCallbackReturn, default_status_code: int
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


def blueprint_error_handler(exc: Exception) -> ViewReturn:
    # ActionProviderToolsException is the base class for HTTP-based exceptions,
    # return those directly
    if isinstance(exc, ActionProviderToolsException):
        return exc

    # If a component in the toolkit throw's an unhandled AuthenticationError,
    # replace it with a Flask-based response
    if isinstance(exc, AuthenticationError):
        return UnauthorizedRequest()

    current_app.logger.exception("Handling unexpected exception", exc_info=True)
    # Handle unexpected Exceptions in a somewhat predictable way
    resp = {
        "code": ActionProviderError.__name__,
        "description": "Internal Server Error",
    }
    return jsonify(resp), 500


def validate_input(
    request_json: Any, input_body_validator: ActionInputValidatorType
) -> ActionRequest:
    """
    Verify the incoming request is a JSON object that conforms to the required schemata.
    This includes both the Action Request schema and the user-defined input schema.
    """

    try:
        # Enforce that the request is a JSON object,
        # then enforce that the object conforms to schema requirements.
        request_json = RequestObject.parse_obj(request_json).__root__
        action_request = ActionRequest(**request_json)
    except ValidationError as ve:
        messages = [f"Field '{'.'.join(e['loc'])}': {e['msg']}" for e in ve.errors()]
        raise RequestValidationError("; ".join(messages))

    input_body_validator(action_request.body)

    return action_request


def get_input_body_validator(
    provider_description: ActionProviderDescription,
    config: ActionProviderConfig = DEFAULT_CONFIG,
) -> ActionInputValidatorType:
    """
    Inspects the value of the provider_description's input_schema to
    determine if it's a str, dict, or pydantic Model to figure out which
    validation function to use.

    If the input_schema is a str or dict, raw json_schema validation will
    be used. A jsonschema Validator is created and applied to
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

    validator_cls = jsonschema.validators.validator_for(input_schema)
    validator = validator_cls(input_schema)

    return partial(
        json_schema_input_validation,
        validator=validator,
        scrub_validation_errors=config.scrub_validation_errors,
    )


def json_schema_input_validation(
    action_input: dict[str, Any],
    validator: jsonschema.Validator,
    scrub_validation_errors: bool = True,
) -> None:
    """
    Use a created JSON Validator to verify the input body of an incoming
    request conforms to the defined JSON schema. In the event that the
    validation reports any errors, a BadActionRequest exception gets raised.
    """
    result = validate_data(action_input, validator, scrub_validation_errors)
    if result.errors:
        raise RequestValidationError(result.error_msg)


def pydantic_input_validation(
    action_input: dict[str, Any], validator: type[BaseModel]
) -> None:
    """
    Validate input using the pydantic model itself. Raises a BadActionRequest
    exception if the input is incorrect.
    """
    try:
        validator(**action_input)
    except ValidationError as ve:
        messages = []
        for error in ve.errors():
            field = _loc_to_json_path(error["loc"])
            messages.append(format_validation_error(field, error["type"], error["msg"]))
        raise RequestValidationError("; ".join(messages))


def _loc_to_json_path(loc: Loc) -> str:
    """
    Transforms a pydantic loc into a JSONPath.

    Sample Transformations:
        ('foo', 0, 'bar') -> '$.foo[0].bar'
        (0, 'foo') -> '$[0].foo'
        (,) -> '$'
    """
    parts_str = "".join(
        f".{part}" if isinstance(part, str) else f"[{part}]" for part in loc
    )
    return f"${parts_str}"


try:
    from flask.json.provider import DefaultJSONProvider
except ImportError:
    # Flask < 2.2: Use the deprecated JSON encoder interface.
    json_provider_available = False
    JsonProvider: DefaultJSONProvider | None = None
else:
    # Flask >= 2.2: Use the new JSON provider interface.
    json_provider_available = True

    class JsonProvider(DefaultJSONProvider):  # type: ignore[no-redef]
        @staticmethod
        def default(o: Any) -> Any:
            return convert_to_json(o)


def assign_json_provider(app_or_blueprint: flask.Flask | flask.Blueprint):
    """Assign a JSON provider (or simply an encoder) to a Flask app or blueprint.

    As of Flask 2.2.1, the `app.json_encoder` attribute is deprecated.
    In its place, the new `app.json` attribute should be used instead.
    This function will assign to the correct attribute
    and avoid deprecation warnings.
    """

    if json_provider_available:
        assert JsonProvider is not None  # mypy hack
        app_or_blueprint.json = JsonProvider(app_or_blueprint)
    else:
        app_or_blueprint.json_encoder = ActionProviderJsonEncoder
