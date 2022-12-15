import json
import logging
import os
from datetime import datetime, timedelta, timezone
from random import randint
from typing import Any, Dict, Tuple

from flask import Flask, Response, jsonify, request

from examples.whattimeisitrightnow.app import config
from examples.whattimeisitrightnow.app import error as err
from examples.whattimeisitrightnow.app.database import db
from globus_action_provider_tools.authentication import TokenChecker
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
    ActionProviderDescription,
    ActionStatus,
    ActionStatusValue,
)
from globus_action_provider_tools.flask import flask_validate_request
from globus_action_provider_tools.flask.helpers import assign_json_provider

app = Flask(__name__)
assign_json_provider(app)

token_checker = TokenChecker(
    config.client_id, config.client_secret, [config.our_scope], config.token_audience
)

COMPLETE_STATES = (ActionStatusValue.SUCCEEDED, ActionStatusValue.FAILED)
INCOMPLETE_STATES = (ActionStatusValue.ACTIVE, ActionStatusValue.INACTIVE)

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.json")) as f:
    schema = json.load(f)


@app.errorhandler(err.ApiError)
def handle_invalid_usage(error) -> Response:
    response = jsonify(error.to_dict())
    response.status_code = error.status
    return response


@app.before_request
def before_request() -> None:
    """
    Here we handle some authorization and request validation before the request
    ever makes it to our ActionProvider. We also attach authentication
    information to the request to make it easier to inspect.

    flask_validate_request ensurse that we are receiving a valid request
    body from the user.

    token_checker.check_token ensure that the requestor provided a valid,
    Globus recognized token for interacting with the Provider.
    """
    validation_result = flask_validate_request(request)
    if validation_result.errors:
        raise err.InvalidRequest(*validation_result.errors)

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    auth_state = token_checker.check_token(token)
    if not auth_state.identities:
        # Returning these authentication errors to the caller will make debugging
        # easier for this example. Consider whether this is appropriate
        # for your production use case or not.
        raise err.NoAuthentication(*auth_state.errors)
    request.auth = auth_state  # type: ignore


@app.route("/", methods=["GET"])
def introspect() -> Tuple[Response, int]:
    """
    The base endpoint of an ActionProvider should serve as documentation,
    enabling users to introspect the JSON schema required to launch an action.
    This endpoint can be publicly accessible or not. The
    ActionProviderDescription visible_to field public access by default.
    """
    description = ActionProviderDescription(
        globus_auth_scope=config.our_scope,
        title="What Time Is It Right Now?",
        admin_contact="support@whattimeisrightnow.example",
        synchronous=False,
        input_schema=schema,
        api_version="1.0",
        subtitle=(
            "From the makers of Philbert: "
            "Another exciting promotional tie-in for whattimeisitrightnow.com"
        ),
        description="",
        keywords=["time", "whattimeisitnow", "productivity"],
        visible_to=["all_authenticated_users"],
        runnable_by=["all_authenticated_users"],
        administered_by=["support@whattimeisrightnow.example"],
    )
    if not request.auth.check_authorization(  # type: ignore
        description.visible_to, allow_all_authenticated_users=True
    ):
        raise err.NotAuthorized("Not visible_to this access token.")
    return jsonify(description), 200


@app.route("/run", methods=["POST"])
def run() -> Tuple[Response, int]:
    """
    This function implements Action Provider interface for launching an
    action instance.

    This function parses the request_id from a request body and from it
    determines whether a new action should be launched or whether to
    return the status of a previously launched action. To accomplish this,
    it is necessary to store a mapping of request_ids to action_ids in
    addition to a history of actions.
    """
    req = request.get_json(force=True)

    # Deduplicate multiple requests based on request_id
    action_id = db.query(req["request_id"])
    if action_id is not None:
        return status(action_id)
    else:
        action_status = run_action(req)
        # Remove any private data from the ActionStatus before
        # returning it to the requestor
        action_status = _filter_private_fields(action_status)
        return jsonify(action_status), 202


def run_action(req) -> ActionStatus:
    """
    A wrapper function to handle executing 'business logic', creating the
    ActionStatus and storing both the request_id:action_id mapping and the
    action_id:action_status mapping.
    """
    now = datetime.now(tz=timezone.utc)

    # Kickoff whatever the action is actually doing
    results = _magic_business_logic(now, req["body"])

    # Create an ActionStatus object with result information
    action_status = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        creator_id=request.auth.effective_identity,  # type: ignore
        label=req.get("label", None),
        monitor_by=req.get("monitor_by", request.auth.identities),  # type: ignore
        manage_by=req.get("manage_by", request.auth.identities),  # type: ignore
        start_time=str(now),
        completion_time=None,
        release_after=req.get("release_after", "P30D"),
        display_status=ActionStatusValue.ACTIVE,
        details=results,
    )

    # Store the request_id for deduplication
    db.persist(req["request_id"], action_status.action_id)

    # Store the details on the running job
    db.persist(action_status.action_id, action_status)
    return action_status


def _filter_private_fields(action_status: ActionStatus) -> ActionStatus:
    """
    Helper function to demonstrate how an ActionStatus object can
    hold private data in its details field and how to filter this
    data before returning an ActionStatus to the requestor
    """
    if action_status.details is not None:
        assert isinstance(action_status.details, dict)
        action_status.details.pop("private", None)
    return action_status


def _magic_business_logic(now, request_body) -> Dict[str, Any]:
    """
    This function computes the current time in a different timezone.
    It accepts "utc_offset" to determine the target timezone before
    converting the time and storing it into the results dictionary.

    This function demonstrates how private data can be computed and
    stored.
    """
    try:
        tz = timezone(timedelta(hours=request_body["utc_offset"]))
    except (KeyError, ValueError) as exc:
        raise err.InvalidRequest("Invalid or missing 'utc_offset'", exc)

    # Simulate some amount of processing time
    estimated_processing_time = randint(5, 900)
    estimated_completion_time = now + timedelta(seconds=estimated_processing_time)

    # 30% of our jobs fail because the universe is an imperfect place
    # and we want clients to understand some providers may fail
    success = randint(1, 100) >= 30
    if success:
        results = {
            "estimated_completion_time": estimated_completion_time,
            "private": {
                "success": True,
                "details": {"whattimeisit": now.astimezone(tz)},
            },
        }
    else:
        results = {
            "estimated_completion_time": estimated_completion_time,
            "private": {
                "success": False,
                "details": {
                    "message": "We didn't know what time it was.",
                    "error": "WATCHLESS",
                },
            },
        }
    return results


@app.route("/<action_id>/status", methods=["GET"])
def status(action_id) -> Tuple[Response, int]:
    """
    This function implements Action Provider interface for looking up an
    action's status. This endpoint is used to query actions that may
    still be executing or may have completed.
    """
    # Ensure the requested action_id exists
    action_status = _get_action_status_or_404(action_id)

    # Ensure the user is authorized to view the action status
    authorize_action_access_or_404(action_status, request.auth)  # type: ignore

    action_status = _reconcile_action_status(action_status)

    # Remove any private data from the ActionStatus before
    # returning it to the requestor
    action_status = _filter_private_fields(action_status)
    return jsonify(action_status), 200


def _get_action_status_or_404(action_id: str) -> ActionStatus:
    """
    Retrieves an action_status from the database
    """
    action_status = db.query(action_id)

    # Since we're using the same database to store action_ids and
    # request_ids, it's possible a user may make a request for an
    # action_id's status using the request_id. In that event, the
    # db lookup for a request_id will return a str.
    if action_status is None or isinstance(action_status, str):
        raise err.NotFound(f"No action instance found for {action_id}")
    return action_status


def _reconcile_action_status(action_status: ActionStatus) -> ActionStatus:
    """
    Helper function to determine if an Action should have completed, and to
    update its status if necessary. If the Action is already in a completed
    state, its record is returned. If the action is still not scheduled to
    complete, its record is returned umodified. If the record was scheduled
    to complete, its status is updated, stored and returned.
    """
    # If status is in a completion state, return
    if action_status.status in COMPLETE_STATES:
        return action_status

    # Make mypy happy...
    if action_status.details is None:
        raise err.DeveloperError(f"{action_status.action_id} has no details.")

    # If it is not yet time for the action to complete, return
    now = datetime.now(tz=timezone.utc)
    assert isinstance(action_status.details, dict)
    if action_status.details["estimated_completion_time"] > now:
        return action_status

    # If the action was scheduled to complete by now, update the ActionStatus
    # object with completion data
    assert isinstance(action_status.details, dict)
    private = action_status.details.pop("private", {})
    action_status.completion_time = action_status.details["estimated_completion_time"]
    action_status.details = private["details"]

    if private["success"]:
        action_status.status = ActionStatusValue.SUCCEEDED
        action_status.display_status = ActionStatusValue.SUCCEEDED
    else:
        action_status.status = ActionStatusValue.FAILED
        action_status.display_status = ActionStatusValue.FAILED

    # Persist updates to the ActionStatus
    db.persist(action_status.action_id, action_status)
    return action_status


@app.route("/<action_id>/cancel", methods=["POST"])
def cancel(action_id: str) -> Tuple[Response, int]:
    """
    This function implements the ActionProvider interface for cancelling an
    action. As noted in the documentation, this operation does not need to
    force the action to immediately cancel.
    """
    # Ensure the requested action_id exists
    action_status = _get_action_status_or_404(action_id)

    # Ensure the user is authorized to manage the action's state
    authorize_action_management_or_404(action_status, request.auth)  # type: ignore

    # Reconcile before cancelling to determine if action already completed
    action_status = _reconcile_action_status(action_status)

    if action_status.status in COMPLETE_STATES:
        raise err.InvalidState(f"Cannot cancel, {action_id} already completed.")

    # Interrupt / cancel the job if it's still running
    action_status = _cancel_job(action_status)
    return jsonify(action_status), 200


def _cancel_job(action_status) -> ActionStatus:
    """
    Helper function used to set an action's status fields to cancelled.
    Once cancelled, updates are persisted to the database.
    """
    action_status.status = ActionStatusValue.FAILED
    action_status.display_status = ActionStatusValue.FAILED
    action_status.completion_time = datetime.now(tz=timezone.utc)
    action_status.details = {"message": "Job cancelled", "error": "CANCELLED"}

    db.persist(action_status.action_id, action_status)
    return action_status


@app.route("/<action_id>/release", methods=["POST"])
def release(action_id: str) -> Tuple[Response, int]:
    """
    Releasing an Action erases all records of its execution from the
    Provider's history. Subsequent lookups for the Action's execution
    will fail.
    """
    # Ensure the requested action_id exists
    action_status = _get_action_status_or_404(action_id)

    # Ensure the user is authorized to manage the action's state
    authorize_action_management_or_404(action_status, request.auth)  # type: ignore

    # Reconcile before cancelling to determine if action already completed
    action_status = _reconcile_action_status(action_status)

    if action_status.status in INCOMPLETE_STATES:
        raise err.InvalidState(f"Cannot release, {action_id} has not completed.")

    db.delete(action_id)
    return jsonify(action_status), 200


def main():
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)


if __name__ == "__main__":
    main()
