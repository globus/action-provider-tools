import logging
import warnings
from typing import List, Optional

import flask
from flask import jsonify, request
from pydantic import ValidationError

from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionProviderJsonEncoder,
    ActionStatusValue,
)
from globus_action_provider_tools.flask.exceptions import (
    ActionNotFound,
    ActionProviderError,
    UnauthorizedRequest,
)
from globus_action_provider_tools.flask.helpers import (
    action_status_return_to_view_return,
    blueprint_error_handler,
    check_token,
    get_input_body_validator,
    parse_query_args,
    query_args_to_enum,
    validate_input,
)
from globus_action_provider_tools.flask.types import (
    ActionCancelType,
    ActionEnumerationType,
    ActionLogType,
    ActionReleaseType,
    ActionRunType,
    ActionStatusReturn,
    ActionStatusType,
    ViewReturn,
)
from globus_action_provider_tools.validation import (
    ValidationRequest,
    ValidationResult,
    request_validator,
)

warnings.warn(
    (
        "The globus_action_provider_tools.flask.api_helpers module is deprecated and will "
        "be removed in 0.12.0. Please consider using the "
        "globus_action_provider_tools.flask.apt_blueprint module instead."
    ),
    DeprecationWarning,
    stacklevel=2,
)


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
    action_enumeration_callback: ActionEnumerationType = None,
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
    input_body_validator = get_input_body_validator(provider_description)
    blueprint.register_error_handler(Exception, blueprint_error_handler)

    @blueprint.route("/", methods=["GET"], strict_slashes=False)
    def action_introspect() -> ViewReturn:
        auth_state = check_token(request, checker)
        if not auth_state.check_authorization(
            provider_description.visible_to,
            allow_public=True,
            allow_all_authenticated_users=True,
        ):
            raise ActionNotFound
        return jsonify(provider_description), 200

    @blueprint.route("/actions", methods=["POST"])
    @blueprint.route("/run", methods=["POST"])
    def action_run() -> ViewReturn:
        auth_state = check_token(request, checker)
        if not auth_state.check_authorization(
            provider_description.runnable_by, allow_all_authenticated_users=True
        ):
            log.info(f"Unauthorized call to action run, errors: {auth_state.errors}")
            raise UnauthorizedRequest
        if blueprint.url_prefix:
            request.path = request.path.lstrip(blueprint.url_prefix)
            if request.url_rule is not None:
                request.url_rule.rule = request.url_rule.rule.lstrip(
                    blueprint.url_prefix
                )

        action_request = validate_input(
            request.get_json(force=True), input_body_validator
        )

        # It's possible the user will attempt to make a malformed ActionStatus -
        # pydantic won't like that. So log and handle the error with a 500
        try:
            status = action_run_callback(action_request, auth_state)
        except ValidationError as ve:
            log.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus"
                f" in {action_run_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError

        return action_status_return_to_view_return(status, 202)

    @blueprint.route("/<string:action_id>/status", methods=["GET"])
    @blueprint.route("/actions/<string:action_id>", methods=["GET"])
    def action_status(action_id: str) -> ViewReturn:
        auth_state = check_token(request, checker)
        try:
            status = action_status_callback(action_id, auth_state)
        except ValidationError as ve:
            log.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus"
                f" in {action_status_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError
        return action_status_return_to_view_return(status, 200)

    @blueprint.route("/<string:action_id>/cancel", methods=["POST"])
    @blueprint.route("/actions/<string:action_id>/cancel", methods=["POST"])
    def action_cancel(action_id: str) -> ViewReturn:
        auth_state = check_token(request, checker)
        try:
            status = action_cancel_callback(action_id, auth_state)
        except ValidationError as ve:
            log.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus"
                f" in {action_cancel_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError
        return action_status_return_to_view_return(status, 200)

    @blueprint.route("/<string:action_id>/release", methods=["POST"])
    @blueprint.route("/actions/<string:action_id>", methods=["DELETE"])
    def action_release(action_id: str) -> ViewReturn:
        auth_state = check_token(request, checker)
        try:
            status = action_release_callback(action_id, auth_state)
        except ValidationError as ve:
            log.error(
                f"ActionProvider attempted to create a non-conformant ActionStatus"
                f" in {action_release_callback.__name__}: {ve.errors()}"
            )
            raise ActionProviderError
        return action_status_return_to_view_return(status, 200)

    if action_log_callback is not None:

        @blueprint.route("/actions/<string:action_id>/log", methods=["GET"])
        @blueprint.route("/<string:action_id>/log", methods=["GET"])
        def action_log(action_id: str) -> ViewReturn:
            auth_state = check_token(request, checker)
            return jsonify({"log": "message"}), 200

    if action_enumeration_callback is not None:

        @blueprint.route("/actions", methods=["GET"])
        def action_enumeration():
            auth_state = check_token(request, checker)

            valid_statuses = set(e.name.casefold() for e in ActionStatusValue)
            statuses = parse_query_args(
                request,
                arg_name="status",
                default_value="active",
                valid_vals=valid_statuses,
            )
            statuses = query_args_to_enum(statuses, ActionStatusValue)
            roles = parse_query_args(
                request,
                arg_name="roles",
                default_value="creator_id",
                valid_vals={"creator_id", "monitor_by", "manage_by"},
            )
            query_params = {"statuses": statuses, "roles": roles}
            return jsonify(action_enumeration_callback(auth_state, query_params)), 200
