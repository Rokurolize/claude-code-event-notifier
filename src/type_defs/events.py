"""Event-related type definitions.

This module contains TypedDict definitions for all event data structures
used in the Discord Notifier system.
"""

from typing import TypedDict, Union, Literal, NotRequired
from src.type_defs.base import SessionAware, TimestampedField
from src.type_defs.tools import ToolInput, ToolResponse


# ------------------------------------------------------------------------------
# EVENT DATA HIERARCHY
# ------------------------------------------------------------------------------


class BaseEventData(SessionAware, TimestampedField):
    """Base event data structure."""

    transcript_path: NotRequired[str]
    hook_event_name: str


class ToolEventDataBase(BaseEventData):
    """Base tool event data structure."""

    tool_name: str
    tool_input: ToolInput


class PreToolUseEventData(ToolEventDataBase):
    """PreToolUse event data structure."""


class PostToolUseEventData(ToolEventDataBase):
    """PostToolUse event data structure."""

    tool_response: ToolResponse


class NotificationEventData(BaseEventData):
    """Notification event data structure."""

    message: str
    title: NotRequired[str]
    level: NotRequired[Literal["info", "warning", "error"]]


class StopEventDataBase(BaseEventData):
    """Base stop event data structure."""

    stop_hook_active: NotRequired[bool]


class StopEventData(StopEventDataBase):
    """Stop event data structure."""

    duration: NotRequired[float]
    tools_used: NotRequired[int]
    messages_exchanged: NotRequired[int]


class SubagentStopEventData(StopEventData):
    """SubagentStop event data structure."""

    task_description: NotRequired[str]
    result: NotRequired[str | dict[str, str | int | float | bool]]
    execution_time: NotRequired[float]
    status: NotRequired[str]


# Union type for all event data
EventData = (
    PreToolUseEventData
    | PostToolUseEventData
    | NotificationEventData
    | StopEventData
    | SubagentStopEventData
    | dict[str, str | int | float | bool]
)


# Export all public types
__all__ = [
    'BaseEventData', 'ToolEventDataBase', 'PreToolUseEventData',
    'PostToolUseEventData', 'NotificationEventData',
    'StopEventDataBase', 'StopEventData', 'SubagentStopEventData',
    'EventData'
]