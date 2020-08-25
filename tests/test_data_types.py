import datetime
import json

import pytest

from globus_action_provider_tools.data_types import (
    ActionProviderJsonEncoder,
    ActionStatus,
    ActionStatusValue,
)


def test_action_status_jsonable():
    action_status = ActionStatus(
        status=ActionStatusValue.SUCCEEDED,
        creator_id=None,
        monitor_by=None,
        manage_by=None,
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED.name,
        details={},
    )
    try:
        # This will fail if ActionProviderJsonEncoder cannot json dump an
        # ActionStatus
        json.dumps(action_status, cls=ActionProviderJsonEncoder)
    except TypeError:
        pytest.fail("Unexpected JSON encoding error")
