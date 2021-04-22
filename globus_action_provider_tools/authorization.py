import logging
from itertools import chain

from globus_action_provider_tools.authentication import AuthState
from globus_action_provider_tools.data_types import ActionStatus
from globus_action_provider_tools.errors import AuthenticationError

log = logging.getLogger(__name__)


def authorize_action_access_or_404(status: ActionStatus, auth_state: AuthState) -> None:
    """
    Determines whether or not a principal is allowed to view an ActionStatus.
    If not allowed to view the ActionStatus, this function will raise an
    AuthenticationError.
    """
    if status.monitor_by is None:
        allowed_set = set([status.creator_id])
    else:
        allowed_set = set(chain([status.creator_id], status.monitor_by))

    authorized = auth_state.check_authorization(
        allowed_set, allow_all_authenticated_users=True
    )
    if not authorized:
        log.info(
            f"None of {auth_state.effective_identity}'s identities are allowed to view "
            f"{status.action_id}. User Identities={auth_state.principals} Allowed "
            f"Identities={allowed_set}"
        )
        raise AuthenticationError(f"No Action with id {status.action_id}")


def authorize_action_management_or_404(
    status: ActionStatus, auth_state: AuthState
) -> None:
    """
    Determines whether or not a principal is allowed to manage an ActionStatus.
    If not allowed to view the ActionStatus, this function will raise an
    AuthenticationError.
    """
    if status.manage_by is None:
        allowed_set = set([status.creator_id])
    else:
        allowed_set = set(chain([status.creator_id], status.manage_by))

    authorized = auth_state.check_authorization(
        allowed_set, allow_all_authenticated_users=True
    )
    if not authorized:
        log.info(
            f"None of {auth_state.effective_identity}'s identities are allowed to manage "
            f"{status.action_id}. User Identities={auth_state.principals} Allowed "
            f"Identities={allowed_set}"
        )
        raise AuthenticationError(f"No Action with id {status.action_id}")
