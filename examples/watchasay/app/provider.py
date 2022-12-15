import datetime
import json
import os
from typing import Dict, Optional, Set, Tuple

from flask import Blueprint, Flask

from examples.watchasay.app import config
from globus_action_provider_tools import (
    ActionProviderDescription,
    ActionRequest,
    ActionStatus,
    ActionStatusValue,
    AuthState,
)
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.flask import add_action_routes_to_blueprint
from globus_action_provider_tools.flask.exceptions import ActionConflict, ActionNotFound
from globus_action_provider_tools.flask.helpers import assign_json_provider
from globus_action_provider_tools.flask.types import ActionCallbackReturn

# A simulated database mapping input user action requests identifiers to a previously
# seen request id and the corresponding action id
_fake_request_db: Dict[str, Tuple[ActionRequest, str]] = {}

_fake_action_db: Dict[str, ActionStatus] = {}


def _retrieve_action_status(action_id: str) -> ActionStatus:
    status = _fake_action_db.get(action_id)
    if status is None:
        raise ActionNotFound(f"No Action with id {action_id}")
    return status


def load_schema():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.json")
    ) as f:
        schema = json.load(f)
    return schema


def action_enumerate(auth: AuthState, params: Dict[str, Set]):
    """
    This is an optional endpoint, useful for allowing requestors to enumerate
    actions filtered by ActionStatus and role.

    The params argument will always be a dict containing the incoming request's
    validated query arguments. There will be two keys, 'statuses' and 'roles',
    where each maps to a set containing the filter values for the key. A typical
    params object will look like:

        {
            "statuses": {<ActionStatusValue.ACTIVE: 3>},
            "roles": {"creator_id"}
        }

    Notice that the value for the "statuses" key is an Enum value.
    """
    statuses = params["statuses"]
    roles = params["roles"]
    matches = []

    for _, action in _fake_action_db.items():
        if action.status in statuses:
            # Create a set of identities that are allowed to access this action,
            # based on the roles being queried for
            allowed_set = set()
            for role in roles:
                identities = getattr(action, role)
                if isinstance(identities, str):
                    allowed_set.add(identities)
                else:
                    allowed_set.update(identities)

            # Determine if this request's auth allows access based on the
            # allowed_set
            authorized = auth.check_authorization(allowed_set)
            if authorized:
                matches.append(action)

    return matches


def action_run(request: ActionRequest, auth: AuthState) -> ActionCallbackReturn:
    """
    Asynchronous actions most likely need to implement retry logic here to
    prevent duplicate requests with matching request_ids from launching
    another job. In the event that a request with an existing request_id
    and creator_id arrives, this function should simply return the action's
    status via the action_status function.

    Synchronous actions or actions where it makes sense to execute repeated
    runs with the same parameters need not implement retry logic.
    """

    caller_id = auth.effective_identity
    request_id = request.request_id
    full_request_id = f"{caller_id}:{request_id}"
    prev_request = _fake_request_db.get(full_request_id)
    if prev_request is not None:
        # If the a matching ActionRequest has been found, deduplicate the
        # requests and return the Action's status
        if prev_request[0] == request:
            return action_status(prev_request[1], auth)
        # If a pre-existing ActionRequest with different paramters has been
        # found, throw an error as we can't modify an already running Action
        else:
            raise ActionConflict(
                f"Request with id {request_id} already present with different parameters "
            )

    # Local processing happens here
    result_details = {
        # This is safe because the input has been validated against the input schema
        "you_said": request.body["input_string"]
    }

    # Create an ActionStatus that contains the computed results
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=caller_id or "UNKNOWN",
        monitor_by=request.monitor_by,
        manage_by=request.manage_by,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after=request.release_after or "P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details=result_details,
    )

    # Store the request and action_status
    _fake_request_db[full_request_id] = (request, status.action_id)
    _fake_action_db[status.action_id] = status
    return status


def action_status(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    """
    action_status retrieves the most recent state of the action. This endpoint
    requires the user authenticate with a principal value which is in the
    monitor_by list established when the Action was started.
    """
    status = _retrieve_action_status(action_id)
    authorize_action_access_or_404(status, auth)
    return status, 200


def action_cancel(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    """
    Asynchronous actions need not ensure a running action is immediately
    completed or terminated. In this scenario, action_cancel should return
    an action in a non-completion state. If it has completed, return the action's
    status.

    Synchronous actions need not implement any logic in action_cancel. All
    processing happens in the action_run callback so that action_cancel
    simply returns the action_id's status.

    This endpoint requires the user authenticate with a principal value which is
    in the manage_by list established when the Action was started.
    """
    status = _retrieve_action_status(action_id)
    authorize_action_management_or_404(status, auth)

    # If action is already in complete state, return completion details
    if status.status in (ActionStatusValue.SUCCEEDED, ActionStatusValue.FAILED):
        return status

    # Process Action cancellation
    status.status = ActionStatusValue.FAILED
    status.display_status = "Canceled by user request"
    return status


def action_release(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    """
    If the Action is not already in a completion state, action_release should
    return an error as this operation does not attempt to stop execution.
    Synchronous actions need not determine if the action_id is still in a
    processing state. All processing starts and completes in the action_run
    callback so that action_release simply removes the action_id and request_id
    from history and returns the action_id's completion status.

    This endpoint requires the user authenticate with a principal value which is
    in the manage_by list established when the Action was started.
    """
    status = _retrieve_action_status(action_id)
    authorize_action_management_or_404(status, auth)

    # Error if attempt to release an active Action
    if status.status not in (ActionStatusValue.SUCCEEDED, ActionStatusValue.FAILED):
        raise ActionConflict("Action is not complete")

    _fake_action_db.pop(action_id)
    # Both fake and badly inefficient
    remove_req_id: Optional[str] = None
    for req_id, req_and_action_id in _fake_request_db.items():
        if req_and_action_id[1] == action_id:
            remove_req_id = req_id
            break
    if remove_req_id is not None:
        _fake_request_db.pop(remove_req_id)
    return status, 200


def create_app():
    app = Flask(__name__)
    assign_json_provider(app)
    app.url_map.strict_slashes = False

    # Create and define a blueprint onto which the routes will be added
    skeleton_blueprint = Blueprint("skeleton", __name__, url_prefix="/skeleton")

    # Create the ActionProviderDescription with the correct scope and schema
    provider_description = ActionProviderDescription(
        globus_auth_scope=config.our_scope,
        title="skeleton_action_provider",
        admin_contact="support@globus.org",
        synchronous=True,
        input_schema=load_schema(),
        log_supported=False,  # This provider doesn't implement the log callback
        visible_to=["public"],
    )

    # Use the flask helper function to register the endpoint callbacks onto the
    # blueprint
    add_action_routes_to_blueprint(
        blueprint=skeleton_blueprint,
        client_id=config.client_id,
        client_secret=config.client_secret,
        client_name=None,
        provider_description=provider_description,
        action_run_callback=action_run,
        action_status_callback=action_status,
        action_cancel_callback=action_cancel,
        action_release_callback=action_release,
        action_enumeration_callback=action_enumerate,
        additional_scopes=[
            "https://auth.globus.org/scopes/d3a66776-759f-4316-ba55-21725fe37323/secondary_scope"
        ],
    )

    # Register the blueprint with your flask app before returning it
    app.register_blueprint(skeleton_blueprint)
    return app


def main():
    app = create_app()
    app.run(debug=True)


if __name__ == "__main__":
    main()
