from typing import Callable, Dict, Sequence, Set, Tuple, Union

from flask import Response

from globus_action_provider_tools.authentication import AuthState
from globus_action_provider_tools.data_types import (
    ActionLogReturn,
    ActionRequest,
    ActionStatus,
)

ActionCallbackReturn = Union[ActionStatus, Tuple[ActionStatus, int]]
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
    [AuthState, Dict[str, Set]], Sequence[ActionStatus]
]

ViewReturn = Union[Tuple[Response, int], Tuple[str, int]]
