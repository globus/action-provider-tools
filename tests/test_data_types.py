import datetime
import json

import pytest

from globus_action_provider_tools.data_types import (
    ActionProviderJsonEncoder,
    ActionStatus,
    ActionStatusValue,
)

from .utils import random_creator_id


def test_action_status_jsonable():
    action_status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=random_creator_id(),
        monitor_by=[],
        manage_by=set(),
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )
    try:
        # This will fail if ActionProviderJsonEncoder cannot json dump an
        # ActionStatus
        json.dumps(action_status, cls=ActionProviderJsonEncoder)
    except TypeError as e:
        pytest.fail(f"Unexpected JSON encoding error: {e}")
