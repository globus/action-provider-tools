from datetime import datetime, timezone
from typing import Dict, List, Set

from flask import request
from pydantic import BaseModel, Field

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
from globus_action_provider_tools.flask import ActionProviderBlueprint
from globus_action_provider_tools.flask.exceptions import ActionConflict, ActionNotFound
from globus_action_provider_tools.flask.types import (
    ActionCallbackReturn,
    ActionLogReturn,
)

from .backend import simple_backend


class ActionProviderInput(BaseModel):
    utc_offset: int = Field(
        ..., title="UTC Offset", description="An input value to this ActionProvider"
    )

    class Config:
        schema_extra = {"example": {"utc_offset": 10}}


description = ActionProviderDescription(
    globus_auth_scope="https://auth.globus.org/scopes/d3a66776-759f-4316-ba55-21725fe37323/action_all",
    title="What Time Is It Right Now?",
    admin_contact="support@whattimeisrightnow.example",
    synchronous=True,
    input_schema=ActionProviderInput,
    api_version="1.0",
    subtitle="Another exciting promotional tie-in for whattimeisitrightnow.com",
    description="",
    keywords=["time", "whattimeisitnow", "productivity"],
    visible_to=["public"],
    runnable_by=["all_authenticated_users"],
    administered_by=["support@whattimeisrightnow.example"],
)


aptb = ActionProviderBlueprint(
    name="apt",
    import_name=__name__,
    url_prefix="/apt",
    provider_description=description,
)


@aptb.action_enumerate
def action_enumeration(auth: AuthState, params: Dict[str, Set]) -> List[ActionStatus]:
    """
    This is an optional endpoint, useful for allowing requesters to enumerate
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


@aptb.action_run
def my_action_run(
    action_request: ActionRequest, auth: AuthState
) -> ActionCallbackReturn:
    """
    Implement custom business logic related to instantiating an Action here.
    Once launched, collect details on the Action and create an ActionStatus
    which records information on the instantiated Action and gets stored.
    """
    action_status = ActionStatus(
        status=ActionStatusValue.ACTIVE,
        creator_id=str(auth.effective_identity),
        label=action_request.label or None,
        monitor_by=action_request.monitor_by or auth.identities,
        manage_by=action_request.manage_by or auth.identities,
        start_time=datetime.now(timezone.utc).isoformat(),
        completion_time=None,
        release_after=action_request.release_after or "P30D",
        display_status=ActionStatusValue.ACTIVE,
        details={},
    )
    simple_backend[action_status.action_id] = action_status
    return action_status


@aptb.action_status
def my_action_status(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    """
    Query for the action_id in some storage backend to return the up-to-date
    ActionStatus. It's possible that some ActionProviders will require querying
    an external system to get up to date information on an Action's status.
    """
    action_status = simple_backend.get(action_id)
    if action_status is None:
        raise ActionNotFound(f"No action with {action_id}")
    authorize_action_access_or_404(action_status, auth)
    return action_status


@aptb.action_cancel
def my_action_cancel(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    """
    Only Actions that are not in a completed state may be cancelled.
    Cancellations do not necessarily require that an Action's execution be
    stopped. Once cancelled, the ActionStatus object should be updated and
    stored.
    """
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


@aptb.action_release
def my_action_release(action_id: str, auth: AuthState) -> ActionCallbackReturn:
    """
    Only Actions that are in a completed state may be released. The release
    operation removes the ActionStatus object from the data store. The final, up
    to date ActionStatus is returned after a successful release.
    """
    action_status = simple_backend.get(action_id)
    if action_status is None:
        raise ActionNotFound(f"No action with {action_id}")

    authorize_action_management_or_404(action_status, auth)
    if not action_status.is_complete():
        raise ActionConflict("Cannot release incomplete Action")

    action_status.display_status = f"Released by {auth.effective_identity}"
    simple_backend.pop(action_id)
    return action_status


@aptb.action_log
def my_action_log(action_id: str, auth: AuthState) -> ActionLogReturn:
    """
    Action Providers can optionally support a logging endpoint to return
    detailed information on an Action's execution history. Pagination and
    filters are supported as query parameters and can be used to control what
    details are returned to the requester.
    """
    pagination = request.args.get("pagination")
    filters = request.args.get("filters")
    return ActionLogReturn(
        code=200,
        description=f"This is an example of a detailed log entry for {action_id}",
        **{
            "time": "TODAY",
            "details": {
                "action_id": "Transfer",
                "filters": filters,
                "pagination": pagination,
            },
        },
    )
