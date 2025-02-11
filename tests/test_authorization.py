import datetime
import uuid

import pytest

from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import ActionStatus, ActionStatusValue
from globus_action_provider_tools.errors import AuthenticationError


@pytest.fixture
def random_identity_urn():
    return f"urn:globus:auth:identity:{uuid.uuid4()}"


def test_creator_can_access(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=auth_state.effective_identity,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )

    authorize_action_access_or_404(status, auth_state)


def test_monitor_by_can_access(auth_state, random_identity_urn):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=random_identity_urn,
        monitor_by={auth_state.effective_identity},
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )

    authorize_action_access_or_404(status, auth_state)


def test_unauthorized_access(auth_state, random_identity_urn):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=random_identity_urn,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )

    with pytest.raises(AuthenticationError):
        authorize_action_access_or_404(status, auth_state)


def test_creator_can_manage(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=auth_state.effective_identity,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )

    authorize_action_management_or_404(status, auth_state)


def test_manage_by_can_access(auth_state, random_identity_urn):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=random_identity_urn,
        manage_by={auth_state.effective_identity},
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )

    authorize_action_management_or_404(status, auth_state)


def test_unauthorized_management(auth_state, random_identity_urn):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=random_identity_urn,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )

    with pytest.raises(AuthenticationError):
        authorize_action_management_or_404(status, auth_state)
