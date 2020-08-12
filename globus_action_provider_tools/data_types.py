import datetime
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum, auto
from json import JSONEncoder
from os import urandom
from typing import Any, Dict, List, NamedTuple, Optional, Union

import arrow
from base62 import encodebytes as base62

from .authentication import AuthState


def now_isoformat():
    return str(arrow.get().datetime)


def shortish_id() -> str:
    """Generate a random relatively short string of URL safe alphanumeric characters. Value
    space is sufficiently large that the odds of collision are extremely low.
    """
    return base62(urandom(9))


class ProviderType(Enum):
    Action = auto()
    Event = auto()


class EventType(Enum):
    STARTED = auto()
    STATUS_UPDATE = auto()
    LOG_UPDATE = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class ActionProviderDescription:
    globus_auth_scope: str
    title: str
    admin_contact: str
    synchronous: bool
    input_schema: Union[str, Dict[str, Any]]
    types: List[ProviderType] = field(default_factory=lambda: [ProviderType.Action])
    api_version: str = "1.0"
    subtitle: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    visible_to: List[str] = field(default_factory=lambda: ["public"])
    maximum_deadline: str = "P30D"  # Default value of 30 days
    log_supported: Optional[bool] = False
    runnable_by: List[str] = field(default_factory=lambda: ["all_authenticated_users"])
    administered_by: Optional[List[str]] = None
    event_types: Optional[List[EventType]] = None


@dataclass
class ActionRequest:
    request_id: str
    body: Dict[str, Any]
    label: Optional[str] = None
    monitor_by: Optional[List[str]] = None
    manage_by: Optional[List[str]] = None
    allowed_clients: Optional[List[str]] = None
    deadline: Optional[str] = None
    release_after: Optional[str] = None


class ActionStatusValue(Enum):
    SUCCEEDED = auto()
    FAILED = auto()
    ACTIVE = auto()
    INACTIVE = auto()


@dataclass
class ActionStatus:
    status: ActionStatusValue
    creator_id: str
    action_id: str = field(default_factory=shortish_id)
    start_time: str = field(default_factory=now_isoformat)
    label: Optional[str] = None
    monitor_by: Optional[List[str]] = None
    manage_by: Optional[List[str]] = None
    completion_time: Optional[str] = None
    release_after: Optional[str] = None
    display_status: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def is_complete(self):
        return self.status in (ActionStatusValue.SUCCEEDED, ActionStatusValue.FAILED)


class ActionProviderJsonEncoder(JSONEncoder):
    def default(self, obj):
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, Enum):
            return obj.name
        return super(ActionProviderJsonEncoder, self).default(obj)
