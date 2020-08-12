from werkzeug.exceptions import NotFound

from .authentication import AuthState
from .data_types import ActionStatus


def authorize_action_access_or_404(status: ActionStatus, auth_state: AuthState) -> None:
    """
    Determines whether or not a principal is allowed to view an ActionStatus.
    If not allowed to view the ActionStatus, this function will raise a 
    404 error indicating that the requested action was not found.
    """
    if status.monitor_by is None:
        allowed_set = set([status.creator_id])
    else:
        allowed_set = set([status.creator_id] + status.monitor_by)

    authorized = auth_state.check_authorization(
        allowed_set, allow_all_authenticated_users=True
    )
    if not authorized:
        raise NotFound(f"No Action with id {status.action_id}")


def authorize_action_management_or_404(
    status: ActionStatus, auth_state: AuthState
) -> None:
    """
    Determines whether or not a principal is allowed to manage an ActionStatus.
    If not allowed to manage the ActionStatus, this function will raise a 
    404 error indicating that the requested action was not found.
    """
    if status.manage_by is None:
        allowed_set = set([status.creator_id])
    else:
        allowed_set = set([status.creator_id] + status.manage_by)

    authorized = auth_state.check_authorization(
        allowed_set, allow_all_authenticated_users=True
    )
    if not authorized:
        raise NotFound(f"No Action with id {status.action_id}")
