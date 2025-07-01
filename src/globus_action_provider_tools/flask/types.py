from collections.abc import Sequence
from typing import Callable, Union

from flask import Response

from globus_action_provider_tools.authentication import AuthState
from globus_action_provider_tools.data_types import (
    ActionLogReturn,
    ActionRequest,
    ActionStatus,
)

ActionCallbackReturn = Union[ActionStatus, tuple[ActionStatus, int]]
ActionOperationCallback = Union[
    Callable[[str, AuthState], ActionCallbackReturn],
    Callable[[ActionStatus, AuthState], ActionCallbackReturn],
]

ActionRunCallback = Callable[[ActionRequest, AuthState], ActionCallbackReturn]
ActionStatusCallback = ActionOperationCallback
ActionResumeCallback = ActionOperationCallback
ActionCancelCallback = ActionOperationCallback
ActionReleaseCallback = ActionOperationCallback
ActionLogCallback = Callable[[str, AuthState], ActionLogReturn]
ActionEnumerationCallback = Callable[
    [AuthState, dict[str, set]], Sequence[ActionStatus]
]

ViewReturn = Union[tuple[Response, int], tuple[str, int]]
