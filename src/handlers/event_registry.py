#!/usr/bin/env python3
"""Event formatter registry for Discord Notifier.

This module provides a registry pattern implementation for managing
event type to formatter function mappings.
"""

from collections.abc import Callable
from typing import Union

from src.core.constants import EventTypes
from src.core.http_client import DiscordEmbed
from src.formatters.event_formatters import (
    NotificationEventData,
    StopEventData,
    SubagentStopEventData,
    ToolEventData,
    format_default_impl,
    format_notification,
    format_post_tool_use,
    format_pre_tool_use,
    format_stop,
    format_subagent_stop,
)

# Type alias for event data
EventData = Union[
    ToolEventData,
    NotificationEventData,
    StopEventData,
    SubagentStopEventData,
    dict[str, str | int | float | bool],
]


class FormatterRegistry:
    """Registry for event formatters.

    This class implements a registry pattern to map event types to their
    corresponding formatter functions. It provides a centralized way to
    manage formatters and allows for runtime registration of new formatters.

    Attributes:
        _formatters: Dictionary mapping event types to formatter functions

    Example:
        >>> registry = FormatterRegistry()
        >>> formatter = registry.get_formatter("PreToolUse")
        >>> embed = formatter(event_data, session_id)
    """

    def __init__(self) -> None:
        """Initialize the formatter registry with default formatters."""
        self._formatters: dict[str, Callable[[EventData, str], DiscordEmbed]] = {
            EventTypes.PRE_TOOL_USE.value: format_pre_tool_use,
            EventTypes.POST_TOOL_USE.value: format_post_tool_use,
            EventTypes.NOTIFICATION.value: format_notification,
            EventTypes.STOP.value: format_stop,
            EventTypes.SUBAGENT_STOP.value: format_subagent_stop,
        }

    def get_formatter(self, event_type: str) -> Callable[[EventData, str], DiscordEmbed]:
        """Get formatter for event type.

        Args:
            event_type: The type of event to get formatter for

        Returns:
            Formatter function for the event type. If no specific formatter
            is registered, returns a default formatter that handles unknown
            event types.

        Example:
            >>> formatter = registry.get_formatter("PreToolUse")
            >>> # Returns format_pre_tool_use function

            >>> formatter = registry.get_formatter("UnknownEvent")
            >>> # Returns lambda that calls format_default_impl
        """
        if event_type in self._formatters:
            return self._formatters[event_type]
        # Return a lambda that captures the event_type for unknown events
        return lambda event_data, session_id: format_default_impl(event_type, event_data, session_id)

    def register(
        self,
        event_type: str,
        formatter: Callable[[EventData, str], DiscordEmbed],
    ) -> None:
        """Register a new formatter.

        Args:
            event_type: The event type to register formatter for
            formatter: The formatter function that takes event_data and session_id
                      and returns a DiscordEmbed

        Example:
            >>> def format_custom(event_data: dict[str, str | int | float | bool], session_id: str) -> DiscordEmbed:
            ...     return {"title": "Custom Event", "description": "..."}
            >>> registry.register("CustomEvent", format_custom)
        """
        self._formatters[event_type] = formatter
