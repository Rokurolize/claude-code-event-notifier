#!/usr/bin/env python3
"""Event formatter registry for Discord Notifier.

This module provides a registry pattern implementation for managing
event type to formatter function mappings.
"""

from collections.abc import Callable
from typing import Union, cast

from src.constants import EventTypes
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
from src.utils.astolfo_logger import AstolfoLogger

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
        _logger: AstolfoLogger instance for logging operations

    Example:
        >>> registry = FormatterRegistry()
        >>> formatter = registry.get_formatter("PreToolUse")
        >>> embed = formatter(event_data, session_id)
    """

    def __init__(self) -> None:
        """Initialize the formatter registry with default formatters."""
        self._logger = AstolfoLogger()
        self._formatters: dict[str, Callable[[EventData, str], DiscordEmbed]] = {
            EventTypes.PRE_TOOL_USE.value: cast(Callable[[EventData, str], DiscordEmbed], format_pre_tool_use),
            EventTypes.POST_TOOL_USE.value: cast(Callable[[EventData, str], DiscordEmbed], format_post_tool_use),
            EventTypes.NOTIFICATION.value: cast(Callable[[EventData, str], DiscordEmbed], format_notification),
            EventTypes.STOP.value: cast(Callable[[EventData, str], DiscordEmbed], format_stop),
            EventTypes.SUBAGENT_STOP.value: cast(Callable[[EventData, str], DiscordEmbed], format_subagent_stop),
        }
        
        self._logger.info(
            "FormatterRegistry initialized",
            {
                "registered_formatters": list(self._formatters.keys()),
                "formatter_count": len(self._formatters),
            }
        )

    def get_formatter(
        self, event_type: str
    ) -> Callable[[EventData, str], DiscordEmbed]:
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
            self._logger.debug(
                "Formatter found for event type",
                {
                    "event_type": event_type,
                    "formatter": self._formatters[event_type].__name__,
                }
            )
            return self._formatters[event_type]
        
        self._logger.warning(
            "No formatter found for event type, using default",
            {
                "event_type": event_type,
                "available_formatters": list(self._formatters.keys()),
            }
        )
        # Return a lambda that captures the event_type for unknown events
        return lambda event_data, session_id: format_default_impl(event_type, cast(dict[str, str | int | float | bool], event_data), session_id)

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
        was_replaced = event_type in self._formatters
        old_formatter = self._formatters.get(event_type)
        
        self._formatters[event_type] = formatter
        
        if was_replaced:
            self._logger.warning(
                "Replaced existing formatter",
                {
                    "event_type": event_type,
                    "old_formatter": old_formatter.__name__ if old_formatter else None,
                    "new_formatter": formatter.__name__,
                }
            )
        else:
            self._logger.info(
                "Registered new formatter",
                {
                    "event_type": event_type,
                    "formatter": formatter.__name__,
                    "total_formatters": len(self._formatters),
                }
            )
