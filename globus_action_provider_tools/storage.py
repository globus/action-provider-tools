import typing as t
from abc import ABC, abstractmethod

from globus_action_provider_tools.data_types import ActionStatus


class AbstractActionRepository(ABC):
    @abstractmethod
    def get(self, action_id: str) -> t.Optional[ActionStatus]: ...

    @abstractmethod
    def store(self, action: ActionStatus): ...

    @abstractmethod
    def remove(self, action: ActionStatus): ...
