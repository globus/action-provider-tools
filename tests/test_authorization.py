import datetime

import pytest
from werkzeug.exceptions import NotFound

from globus_action_provider_tools.authorization import (
    authorize_action_access_or_404,
    authorize_action_management_or_404,
)
from globus_action_provider_tools.data_types import ActionStatus, ActionStatusValue


def test_creator_can_access(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED.name,
        creator_id=auth_state.effective_identity,
        monitor_by=None,
        manage_by=None,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )

    authorize_action_access_or_404(status, auth_state)


def test_monitor_by_can_access(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED.name,
        creator_id="",
        monitor_by=[auth_state.effective_identity],
        manage_by=None,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )

    authorize_action_access_or_404(status, auth_state)


def test_unauthorized_access(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED.name,
        creator_id="",
        monitor_by=None,
        manage_by=None,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )

    with pytest.raises(NotFound):
        authorize_action_access_or_404(status, auth_state)


def test_creator_can_manage(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED.name,
        creator_id=auth_state.effective_identity,
        monitor_by=None,
        manage_by=None,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )

    authorize_action_management_or_404(status, auth_state)


def test_manage_by_can_access(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED.name,
        creator_id="",
        monitor_by="",
        manage_by=[auth_state.effective_identity],
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )

    authorize_action_management_or_404(status, auth_state)


def test_unauthorized_management(auth_state):
    status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED.name,
        creator_id="",
        monitor_by=None,
        manage_by=None,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )

    with pytest.raises(NotFound):
        authorize_action_management_or_404(status, auth_state)
