import datetime
import json
import uuid

import pytest
from pydantic import BaseModel

from globus_action_provider_tools.data_types import (
    ActionProviderJsonEncoder,
    ActionStatus,
    ActionStatusValue,
)

ACTION_STATUS_ARGS = dict(
    status=ActionStatusValue.SUCCEEDED,
    creator_id=f"urn:globus:auth:identity:{uuid.uuid4()}",
    monitor_by=set(),
    manage_by=set(),
    completion_time=str(datetime.datetime.now().isoformat()),
    release_after="P30D",
    display_status=ActionStatusValue.SUCCEEDED,
    details={},
)


@pytest.mark.parametrize(
    "kwargs",
    [
        ACTION_STATUS_ARGS,
        {**ACTION_STATUS_ARGS, "start_time": str(datetime.datetime.now().isoformat())},
    ],
)
def test_action_status_jsonable(kwargs):
    action_status = ActionStatus(**kwargs)
    # This will fail if ActionProviderJsonEncoder cannot json dump an
    # ActionStatus or if the dumped ActionStatus cannot be parsed as a valid
    # ActionStatus
    action_str = ActionProviderJsonEncoder().encode(action_status)
    ActionStatus.parse_raw(action_str)


def test_pydantic_models_jsonable():
    class PydanticModel(BaseModel): ...

    ActionProviderJsonEncoder().encode(PydanticModel)
    ActionProviderJsonEncoder().encode(PydanticModel())


def test_enums_jsonable():
    assert json.dumps(ActionStatusValue.SUCCEEDED) == '"SUCCEEDED"'
