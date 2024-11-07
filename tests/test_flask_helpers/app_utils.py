from datetime import datetime, timezone
from typing import Dict, List, Set

from flask import request
from pydantic import BaseModel, Field

from globus_action_provider_tools import AuthState
from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import (
    ActionLogEntry,
    ActionLogReturn,
    ActionProviderDescription,
    ActionRequest,
    ActionStatus,
    ActionStatusValue,
)
from globus_action_provider_tools.flask.exceptions import ActionConflict, ActionNotFound
from globus_action_provider_tools.flask.types import ActionCallbackReturn

simple_backend: Dict[str, ActionStatus] = {}

action_provider_json_input_schema = {
    "$id": "whattimeisitnow.provider.input.schema.json",
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Test Provider Input Schema",
    "type": "object",
    "properties": {"echo_string": {"type": "string"}},
    "required": ["echo_string"],
    "additionalProperties": False,
}


class ActionProviderPydanticInputSchema(BaseModel):
    echo_string: str = Field(
        ...,
        title="Echo String",
        description="An input value to this ActionProvider to echo back in its response",
    )

    class Config:
        schema_extra = {"example": {"echo_string": "hi there"}}


ap_description = ActionProviderDescription(
    globus_auth_scope="https://auth.globus.org/scopes/d3a66776-759f-4316-ba55-21725fe37323/action_all",
    title="Test ActionProviderDescription",
    admin_contact="test@globus.org",
    synchronous=True,
    input_schema=action_provider_json_input_schema,
    api_version="1.0",
    subtitle="Test ActionProviderDescription",
    description="Only for Testing",
    keywords=["Testing"],
    visible_to=["public"],
    runnable_by=["all_authenticated_users"],
    administered_by=["test@globus.org"],
)


def mock_action_enumeration_func(
    auth: AuthState, params: Dict[str, Set]
) -> List[ActionStatus]:
    statuses = params["statuses"]
    roles = params["roles"]
    matches = []

    for _, action in simple_backend.items():
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


def mock_action_run_func(
    action_request: ActionRequest, auth: AuthState
) -> ActionCallbackReturn:
    action_status = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        creator_id=str(auth.effective_identity),
        label=action_request.label or None,
        monitor_by=action_request.monitor_by or auth.identities,
        manage_by=action_request.manage_by or auth.identities,
        start_time=str(datetime.now(tz=timezone.utc)),
        completion_time=None,
        release_after=action_request.release_after or "P30D",
        display_status=ActionStatusValue.ACTIVE,
        details={},
    )
    simple_backend[action_status.action_id] = action_status
    return action_status


def mock_action_status_func(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    action_status = simple_backend.get(action_id)
    if action_status is None:
        raise ActionNotFound(f"No action with {action_id}")
    authorize_action_access_or_404(action_status, auth)
    return action_status


def mock_action_cancel_func(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    action_status = simple_backend.get(action_id)
    if action_status is None:
        raise ActionNotFound(f"No action with {action_id}")

    authorize_action_management_or_404(action_status, auth)
    if action_status.is_complete():
        raise ActionConflict("Cannot cancel complete action")

    action_status.status = ActionStatusValue.FAILED
    action_status.display_status = f"Cancelled by {auth.effective_identity}"
    simple_backend[action_id] = action_status

    return action_status


def mock_action_release_func(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    action_status = simple_backend.get(action_id)
    if action_status is None:
        raise ActionNotFound(f"No action with {action_id}")

    authorize_action_management_or_404(action_status, auth)
    if not action_status.is_complete():
        raise ActionConflict("Cannot release incomplete Action")

    action_status.display_status = f"Released by {auth.effective_identity}"
    simple_backend.pop(action_id)
    return action_status


def mock_action_log_func(action_id: str, auth: AuthState) -> ActionLogReturn:
    pagination = request.args.get("pagination")
    filters = request.args.get("filters")
    return ActionLogReturn(
        code=200,
        description=f"This is an example of a detailed log entry for {action_id}",
        limit=1,
        has_next_page=False,
        entries=[
            ActionLogEntry(
                code="GenericLogEntry",
                description="Description of log entry",
                details={
                    "action_id": "Transfer",
                    "filters": filters,
                    "pagination": pagination,
                },
            )
        ],
    )
