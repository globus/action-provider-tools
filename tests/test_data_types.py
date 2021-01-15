import datetime
import json

import pytest
from pydantic import BaseModel, ValidationError

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
        monitor_by=set(),
        manage_by=set(),
        start_time=str(datetime.datetime.now().isoformat()),
        completion_time=str(datetime.datetime.now().isoformat()),
        release_after="P30D",
        display_status=ActionStatusValue.SUCCEEDED,
        details={},
    )
    try:
        # This will fail if ActionProviderJsonEncoder cannot json dump an
        # ActionStatus or if the dumped ActionStatus cannot be parsed as a valid
        # ActionStatus
        action_str = json.dumps(action_status, cls=ActionProviderJsonEncoder)
        ActionStatus.parse_raw(action_str)
    except TypeError as e:
        pytest.fail(f"Unexpected JSON encoding error: {e}")
    except ValidationError as e:
        pytest.fail(f"Unexpected validation error creating ActionStatus from str: {e}")


def test_pydantic_models_jsonable():
    class PydanticModel(BaseModel):
        ...

    try:
        json.dumps(PydanticModel, cls=ActionProviderJsonEncoder)
        json.dumps(PydanticModel(), cls=ActionProviderJsonEncoder)
    except TypeError as e:
        pytest.fail(f"Unexpected JSON encoding error: {e}")


def test_enums_jsonable():
    try:
        json.dumps(ActionStatusValue.SUCCEEDED)
    except TypeError as e:
        pytest.fail(f"Unexpected JSON encoding error: {e}")
