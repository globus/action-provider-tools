from typing import Any, Callable, Dict, Sequence, Set, Tuple, Union

from flask import Response

from globus_action_provider_tools.authentication import AuthState
from globus_action_provider_tools.data_types import (
    ActionLogReturn,
    ActionRequest,
    ActionStatus,
)

ActionStatusReturn = Union[ActionStatus, Tuple[ActionStatus, int]]
ActionStatusType = Callable[[Union[str, ActionStatus], AuthState], ActionStatusReturn]

ActionLogType = Callable[[str, AuthState], ActionLogReturn]

ActionRunType = Callable[[ActionRequest, AuthState], ActionStatusReturn]
ActionCancelType = ActionStatusType
ActionReleaseType = ActionStatusType
ActionEnumerationType = Callable[[AuthState, Dict[str, Set]], Sequence[ActionStatus]]

ViewReturn = Union[Tuple[Response, int], Tuple[str, int]]

ActionLoaderType = Tuple[Callable[[str, Any], ActionStatus], Any]
ActionSaverType = Tuple[Callable[[ActionStatus, Any], None], Any]
