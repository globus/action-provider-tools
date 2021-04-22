import datetime
import inspect
from enum import Enum
from json import JSONEncoder
from typing import AbstractSet, Any, Dict, List, Optional, Set, Type, Union

import isodate
from pydantic import BaseModel, Field

from globus_action_provider_tools.utils import (
    now_isoformat,
    principal_urn_regex,
    shortish_id,
    uuid_regex,
)


class AutomateBaseEnum(str, Enum):
    """
    A pythonic Enum class implementation that removes the need to access a
    "value" attribute to get an Enum's representation.
    http://www.cosmicpython.com/blog/2020-10-27-i-hate-enums.html
    """

    def __str__(self) -> str:
        return str.__str__(self)


class ProviderType(AutomateBaseEnum):
    Action = "ACTION"
    Event = "EVENT"


class EventType(AutomateBaseEnum):
    STARTED = "STARTED"
    STATUS_UPDATE = "STATUS_UPDATE"
    LOG_UPDATE = "LOG_UPDATE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ActionStatusValue(AutomateBaseEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ActionProviderDescription(BaseModel):
    globus_auth_scope: str
    title: str
    admin_contact: str
    synchronous: bool
    input_schema: Union[str, Dict[str, Any], Type[BaseModel]]
    types: List[ProviderType] = Field(default_factory=lambda: [ProviderType.Action])
    api_version: str = "1.0"
    subtitle: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[List[str]] = None
    visible_to: List[str] = Field(default_factory=lambda: ["public"])
    maximum_deadline: str = "P30D"  # Default value of 30 days
    log_supported: Optional[bool] = False
    runnable_by: List[str] = Field(default_factory=lambda: ["all_authenticated_users"])
    administered_by: Optional[List[str]] = None
    event_types: Optional[List[EventType]] = None


class ActionRequest(BaseModel):
    request_id: str = Field(
        ...,
        description=(
            "A unique identifier representing the request to start an action. "
            "Multiple uses of the same request_id must have the same content or they "
            "will be rejected. Only one instance of the operation will be "
            "executed, so requests with the same request_id may be repeated "
            "to attempt to guarantee execution of an action"
        ),
    )
    body: Dict[str, Any] = Field(
        ...,
        description=(
            "The Action Provider-specific content describing the action "
            "to run. The format for the body is provided in the "
            "input_schema field of the Action Provider Description"
        ),
    )
    label: Optional[str] = Field(
        None,
        description="A short human presentable description of the Action requested",
        min_length=1,
        max_length=64,
    )
    deadline: Optional[datetime.datetime] = Field(
        None,
        description=(
            "A timestamp indicating by which time the action must complete. "
            "The request may be rejected if the Action Provider does not expect "
            "to be able to complete the action before the deadline or if it "
            "represents a time greater than the maximum_deadline specified in the "
            "Provider Description."
        ),
    )
    release_after: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "An ISO8601 time duration value indicating how long retention of the "
            "status of the action be retained after it reaches a completed state. "
            "Action Providers may limit the maximum value. It is recommended "
            "that Providers provide a default release_after value of approximately "
            "30 days."
        ),
    )
    monitor_by: Set[str] = Field(
        default_factory=set,
        description=(
            "A list of principal URNs containing identities which are allowed "
            "to monitor the progress of the action using the status and log "
            "operations. When not provided, defaults to the user that initiated "
            "the action."
        ),
        regex=principal_urn_regex,
    )
    manage_by: Set[str] = Field(
        default_factory=set,
        description=(
            "A list of principal URNs containing identities which are allowed to "
            "manage the progress of the action using the cancel and release "
            "operations. When not provided, defaults to the user that initiated "
            "the action."
        ),
        regex=principal_urn_regex,
    )
    allowed_clients: List[str] = Field(
        default_factory=list, regex="^(public|globus|creator|.$)$"
    )


# We provide some helper types for open dict fields like details. But, even when the
# helper type is in place, it can be helpful to have the dict-like behavior to fall back
# on. This MixIn provides support for some dict-like operations, but not all. Beware.
class SubscriptableObject:
    def __getitem__(self, key):
        return vars(self).get(key)

    def __len__(self):
        return len(vars(self))

    def __iter__(self):
        return vars(self).keys()

    def pop(self, key, *args):
        if len(args) > 0:
            return vars(self).pop(key, args[0])
        else:
            return vars(self).pop(key)


class ExtensibleCodeDescription(BaseModel, SubscriptableObject):
    class Config:
        extra = "allow"

    code: str = Field(..., description=(""))
    description: str = Field(..., description=(""))


class ActionFailedDetails(ExtensibleCodeDescription):
    pass


class PaginationWrapper(BaseModel):
    limit: int
    has_next_page: bool
    marker: Optional[str]


class ActionLogEntry(ExtensibleCodeDescription):
    details: Optional[Dict[str, Any]] = Field(None, description=(""))


class ActionLogReturn(PaginationWrapper):
    entries: List[ActionLogEntry]


class ActionInactiveDetails(ExtensibleCodeDescription):
    required_scope: Optional[str] = Field(None, description=(""))
    resolution_url: Optional[str] = Field(None, description=(""))


class ActionStatus(BaseModel):
    status: ActionStatusValue = Field(
        ..., description="The current state of the Action"
    )
    creator_id: str = Field(
        ...,
        description=(
            "A URN representation of an Identity in Globus either of a "
            "user from Globus Auth or a group from Globus Groups."
        ),
        regex=principal_urn_regex,
    )
    action_id: str = Field(
        default_factory=shortish_id, description="The id of the Action itself"
    )
    start_time: str = Field(default_factory=now_isoformat)
    label: Optional[str] = Field(
        None,
        description="A short human presentable description of the Action requested",
        min_length=1,
        max_length=64,
    )
    monitor_by: Set[str] = Field(
        default_factory=set,
        description=(
            "A list of principal URNs containing identities which are allowed to "
            "monitor the progress of the action using the /status and /log operations. "
            "When not provided, defaults to the user that initiated the action."
        ),
        regex=principal_urn_regex,
    )
    manage_by: Set[str] = Field(
        default_factory=set,
        description=(
            "A list of principal URNs containing identities which are allowed "
            "to manage the progress of the action using the cancel and release "
            "operations. When not provided, defaults to the user that initiated "
            "the action."
        ),
        regex=principal_urn_regex,
    )
    completion_time: Optional[datetime.datetime] = Field(
        None,
        description=(
            "The time in ISO8601 format when the Action reached a terminal "
            "(SUCCEEDED or FAILED) status"
        ),
    )
    release_after: Optional[datetime.timedelta] = Field(
        None,
        description=(
            "An ISO8601 time duration value indicating how long retention of "
            "the status of the action be retained after it reaches a completed state."
        ),
    )
    display_status: Optional[str] = Field(
        None,
        description=(
            "A short, human consumable string describing the current status of "
            "this action. This can be used to provide more detailed, presentable "
            "summary of the Action status. For example, a batch system may "
            "use 'Queued' or 'Running' as display_status when the Action has "
            "status 'ACTIVE'. Similarly, a reason the action is blocked, such "
            "as requiring additional authentication may be used when the status "
            "is 'INACTIVE'"
        ),
        min_length=1,
        max_length=64,
    )
    details: Union[ExtensibleCodeDescription, Dict[str, Any], str] = Field(
        ...,
        description=(
            "A provider-specific object representing the full state of the "
            "Action. When the Action is in a SUCCEEDED state, this may be "
            "considered the result or return value from the Action. When "
            "the Action is in a FAILED state, this represents the cause or reason "
            "for failure. While running, the details MAY provide information "
            "about the Action in progress such as a measure of its progress "
            "to completion."
        ),
    )

    def is_complete(self):
        return self.status in (ActionStatusValue.SUCCEEDED, ActionStatusValue.FAILED)


class ActionProviderJsonEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AbstractSet):
            return list(obj)
        elif isinstance(obj, BaseModel):
            return obj.dict()
        elif inspect.isclass(obj) and issubclass(obj, BaseModel):
            return obj.schema()
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return isodate.duration_isoformat(obj)
        return super(ActionProviderJsonEncoder, self).default(obj)
