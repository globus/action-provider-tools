import json
import logging
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from urllib.parse import urlsplit, urlunsplit

import flask
from flask import Request, Response, jsonify, request
from jsonschema.validators import Draft7Validator
from werkzeug.exceptions import BadRequest, HTTPException, NotFound, Unauthorized

from globus_action_provider_tools.authentication import AuthState, TokenChecker
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionProviderJsonEncoder,
    ActionRequest,
    ActionStatus,
)
from globus_action_provider_tools.validation import (
    ValidationRequest,
    ValidationResult,
    request_validator,
)

"""
Removing this for now as it seems that validation breaks more things than it fixes
from globus_action_provider_tools.validation import (
    request_validator,
    response_validator,
)
"""

ActionStatusReturn = Union[ActionStatus, Tuple[ActionStatus, int]]
ViewReturn = Union[Tuple[Response, int], Tuple[str, int]]

ActionRunType = Callable[[ActionRequest, AuthState], ActionStatusReturn]
ActionStatusType = Callable[[str, AuthState], ActionStatusReturn]
ActionCancelType = ActionStatusType
ActionReleaseType = ActionStatusType
ActionLogType = Callable[
    [str, AuthState], Dict[str, Any]
]  # TODO: This is not right at this point


_request_schema_types = {"run": "ActionRequest"}

_response_schema_types = {
    "run": "ActionStatus",
    "status": "ActionStatus",
    "cancel": "ActionStatus",
    "release": "ActionStatus",
}

log = logging.getLogger(__name__)


def _api_operation_for_request(request: flask.Request) -> str:
    method = request.path.rsplit("/", 1)
    op_name = method[-1]
    return op_name


def flask_validate_request(request: flask.Request) -> ValidationResult:
    request_dict = request.get_json(force=True, silent=True)
    op_name = _api_operation_for_request(request)
    doc_type = _request_schema_types.get(op_name)
    if doc_type is not None:
        validation_request = ValidationRequest(
            provider_doc_type=doc_type, request_data=request_dict
        )
        return request_validator(validation_request)
    else:
        return ValidationResult(errors=[], error_msg=None)


def flask_validate_response(
    request: flask.Request, response: flask.Response
) -> ValidationResult:
    response_data = response.get_json(force=True, silent=True)
    op_name = _api_operation_for_request(request)
    doc_type = _response_schema_types.get(op_name)
    # Only do response validation if it is a successful response status
    if doc_type is not None and (200 <= response.status_code < 299):
        validation_request = ValidationRequest(
            provider_doc_type=doc_type, request_data=response_data
        )
        return request_validator(validation_request)
    else:
        return ValidationResult(errors=[], error_msg=None)


def _check_token(request: Request, checker: TokenChecker) -> AuthState:
    access_token = request.headers.get("Authorization", "").strip().lstrip("Bearer ")
    auth_state = checker.check_token(access_token)
    return auth_state


def _action_status_return_to_view_return(
    status: ActionStatusReturn, default_status_code: int
) -> ViewReturn:
    if not isinstance(status, ActionStatus):
        status_code = status[1]
        status = status[0]
    else:
        status_code = default_status_code
    return jsonify(asdict(status)), status_code


def _validate_input(
    validator: Optional[Draft7Validator], input: Dict[str, Any]
) -> None:
    if validator is None:
        return
    errors = validator.iter_errors(input)
    error_messages = []
    for error in errors:
        if error.path:
            # Elements of the error path may be integers or other non-string types,
            # but we need strings for use with join()
            error_path_for_message = ".".join([str(x) for x in error.path])
            error_message = f"'{error_path_for_message}' invalid due to {error.message}"
        else:
            error_message = error.message
        error_messages.append(error_message)

    if error_messages:
        message = "; ".join(error_messages)
        raise BadRequest(message)


def blueprint_error_handler(exc: HTTPException) -> ViewReturn:
    try:
        ret_status = exc.code if exc.code is not None else 500
        return (
            jsonify({"message": exc.description, "status_code": exc.code}),
            ret_status,
        )
    except Exception:
        # This handles the case where the exception type is not expected and doesn't have
        # the description or code attributes
        return (
            jsonify({"message": f"Unexpected Error: {str(exc)}", "status_code": 500}),
            500,
        )


def add_action_routes_to_blueprint(
    blueprint: flask.Blueprint,
    client_id: str,
    client_secret: str,
    client_name: Optional[str],
    provider_description: ActionProviderDescription,
    action_run_callback: ActionRunType,
    action_status_callback: ActionStatusType,
    action_cancel_callback: ActionCancelType,
    action_release_callback: ActionReleaseType,
    action_log_callback: Optional[ActionLogType] = None,
    additional_scopes: Optional[List[str]] = None,
) -> None:
    """Add routes to a Flask Blueprint to implement the required operations of the Action
    Provider Interface: Introspect, Run, Status, Cancel and Release. The route handlers
    added to the blueprint perform basic functionality such as input validation and
    authorization checks where appropriate, and use the provided callbacks to implement
    the action provider specific functionality. See description of each callback below
    for a description of functionality performed prior to invoking the callback.

    **Parameters**

    ``blueprint`` (*Flask.Blueprint*) 
    A flask blueprint to which routes for the URL paths '/', '/run', '/status',
    '/cancel', and '/release' will be added. Optionally, (see below) '/log' will be added
    as well. The blueprint should define a ``url_prefix`` to define a root to the paths
    where these new paths will be added. In addition to the new URL paths, the blueprint
    will also have a custom JSONEncoder associated with it to aid in the serialization of
    data-types associated with these operations.

    ``client_id`` (*string*)
    A Globus Auth registered ``client_id`` which will be used when validating input
    request tokens.

    ``client_secret`` (*string*)
    A Globus Auth generated ``client_secret`` which will be used when validating input
    request tokens.

    ``client_name`` (*string*) Most commonly, this will be a None value. In the rare,
    legacy case where a name has been associated with a client_id, it can be provided
    here. If you are not aware of a name associated with your client_id, it most likely
    doesn't have one and the value should be None. This will be passed to the
    (:class:`TokenChecker<globus_action_provider_tools.authentication>`) as the
    `expected_audience`.

    ``provider_description`` (:class:`ActionProviderDescription\
    <globus_action_provider_tools.data_types>`)
    A structure describing the provider to be returned by the provider introspection
    operation (`GET /`). Some fields are also used in processing requests: the
    `input_schema` field is used to validate the `body` of incoming action requests on
    the `/run` operation. The `globus_auth_scope` value is used to validate the incoming
    tokens on all requests. The `visible_to` and `runnable_by` lists are used to
    authorization operations on the introspect (GET '/') and run (POST '/run') operations
    respectively. The `log_supported` field should be `True` only if the
    `action_log_callback` parameter is provided a value.

    ``action_run_callback`` (* Callable[[ActionRequest, AuthState], Union[ActionStatus,
    Tuple[ActionStatus, int]]] *)
    A function which will be called when an action /run invocation is called. Prior to
    invoking the callback, the handler will validate the input conforms to the Action
    Provider defined request format *and* that the input `body` matches the
    `input_schema` defined in the `provider_description`. It will also authorize the
    caller against the `runnable_by` property of the `provider_description`. In the case
    of any validation or authorization errors, the corresponding werkzeug defined
    exception will be raised. When validation and authorization succeed, the callback
    will be invoked providing the `ActionRequest` structure corresponding to the request
    and the authorization state (`AuthState`) of the caller. The callback should return
    an `ActionStatus` value to be returned on the invocation. Optionally, a status
    integer can be added to the return (making the return a (ActionStatus, int) tuple)
    which defines the HTTP status code to be returned. This is useful in the case where
    an existing request with the same id and body are seen which should return a 200 HTTP
    status rather than the normal 201 HTTP status (which is the default when the status
    code is not returned).

    """
    if additional_scopes:
        all_accepted_scopes = additional_scopes + [
            provider_description.globus_auth_scope
        ]
    else:
        all_accepted_scopes = [provider_description.globus_auth_scope]

    checker = TokenChecker(
        client_id=client_id,
        client_secret=client_secret,
        expected_scopes=all_accepted_scopes,
        expected_audience=client_name,
    )

    blueprint.json_encoder = ActionProviderJsonEncoder

    if isinstance(provider_description.input_schema, str):
        input_schema = json.loads(provider_description.input_schema)
    else:
        input_schema = provider_description.input_schema
    if input_schema is not None:
        input_body_validator = Draft7Validator(input_schema)
    else:
        input_body_validator = None

    blueprint.register_error_handler(Exception, blueprint_error_handler)

    @blueprint.route("/", methods=["GET"], strict_slashes=False)
    def action_introspect() -> ViewReturn:
        auth_state = _check_token(request, checker)
        if not auth_state.check_authorization(
            provider_description.visible_to,
            allow_public=True,
            allow_all_authenticated_users=True,
        ):
            raise NotFound()
        return jsonify(asdict(provider_description)), 200

    @blueprint.route("/run", methods=["POST"])
    def action_run() -> ViewReturn:
        auth_state = _check_token(request, checker)
        if not auth_state.check_authorization(
            provider_description.runnable_by, allow_all_authenticated_users=True
        ):
            log.info(f"Unauthorized call to action run, errors: {auth_state.errors}")
            raise Unauthorized()
        if blueprint.url_prefix:
            request.path = request.path.lstrip(blueprint.url_prefix)
            if request.url_rule is not None:
                request.url_rule.rule = request.url_rule.rule.lstrip(
                    blueprint.url_prefix
                )

        result = flask_validate_request(request)

        if result.error_msg is not None:
            raise BadRequest(result.error_msg)

        request_json = request.get_json(force=True)
        try:
            action_request = ActionRequest(**request_json)
        except TypeError as te:
            # TODO: This is weak validation, but I'll leave for now
            raise BadRequest("Unable to process Action Request input document")
        _validate_input(input_body_validator, action_request.body)
        status = action_run_callback(action_request, auth_state)
        return _action_status_return_to_view_return(status, 201)

    @blueprint.route("/<string:action_id>/status", methods=["GET"])
    def action_status(action_id: str) -> ViewReturn:
        auth_state = _check_token(request, checker)
        return _action_status_return_to_view_return(
            action_status_callback(action_id, auth_state), 200
        )

    @blueprint.route("/<string:action_id>/cancel", methods=["POST"])
    def action_cancel(action_id: str) -> ViewReturn:
        auth_state = _check_token(request, checker)
        return _action_status_return_to_view_return(
            action_cancel_callback(action_id, auth_state), 200
        )

    @blueprint.route("/<string:action_id>/release", methods=["POST"])
    def action_release(action_id: str) -> ViewReturn:
        auth_state = _check_token(request, checker)
        return _action_status_return_to_view_return(
            action_release_callback(action_id, auth_state), 200
        )

    if action_log_callback is not None:

        @blueprint.route("/<string:action_id>/log", methods=["GET"])
        def action_log(action_id: str) -> ViewReturn:
            auth_state = _check_token(request, checker)
            return jsonify({"log": "message"}), 200
