from typing import Dict

from globus_action_provider_tools import ActionStatus
from globus_action_provider_tools.storage import AbstractActionRepository

simple_backend: Dict[str, ActionStatus] = {}


class ActionRepo(AbstractActionRepository):
    repo: dict = {}

    def get(self, action_id: str):
        return self.repo.get(action_id, None)

    def store(self, action: ActionStatus):
        self.repo[action.action_id] = action

    def remove(self, action: ActionStatus):
        del self.repo[action.action_id]
