"""Formatter registry for event type to formatter mapping.

This module provides a registry pattern for managing event formatters,
allowing dynamic registration and lookup of formatters by event type.
"""

from collections.abc import Callable
from typing import Protocol, cast

# Try to import types
try:
    from src.type_defs.events import (
        EventData,
        PreToolUseEventData,
        PostToolUseEventData,
        NotificationEventData,
        StopEventData,
        SubagentStopEventData
    )
    from src.type_defs.discord import DiscordEmbed, DiscordMessage
    from src.type_defs.config import Config
except ImportError:
    # Fallback if modules not available
    from discord_notifier import (  # type: ignore
        EventData, DiscordEmbed, DiscordMessage, Config,
        PreToolUseEventData, PostToolUseEventData,
        NotificationEventData, StopEventData, SubagentStopEventData
    )

# Try to import constants
try:
    from src.constants import EventTypes
except ImportError:
    from discord_notifier import EventTypes  # type: ignore

# Try to import formatters
try:
    from src.formatters.event_formatters import (
        format_pre_tool_use,
        format_post_tool_use,
        format_notification,
        format_stop,
        format_subagent_stop,
        format_default,
    )
except ImportError:
    # These will be provided by discord_notifier
    from discord_notifier import (  # type: ignore
        format_pre_tool_use,
        format_post_tool_use,
        format_notification,
        format_stop,
        format_subagent_stop,
        format_default,
    )


class EventFormatter(Protocol):
    """Protocol for event formatter functions."""
    
    def __call__(self, event_data: EventData, session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed.
        
        Args:
            event_data: Event-specific data
            session_id: Session identifier
            
        Returns:
            Formatted Discord embed
        """
        ...


def _create_default_formatter(event_type: str) -> EventFormatter:
    """Create a default formatter for unknown event types.
    
    Args:
        event_type: The event type to create formatter for
        
    Returns:
        EventFormatter that handles the event as a generic dict
    """
    def formatter(event_data: EventData, session_id: str) -> DiscordEmbed:
        # Cast to dict for format_default which expects dict type
        data_dict = cast(dict[str, str | int | float | bool], event_data)
        return cast(DiscordEmbed, format_default(data_dict, session_id))
    
    return formatter


class FormatterRegistry:
    """Registry for event formatters.
    
    This class maintains a mapping between event types and their corresponding
    formatter functions. It supports dynamic registration of new formatters
    and provides a default formatter for unknown event types.
    
    Example:
        >>> registry = FormatterRegistry()
        >>> formatter = registry.get_formatter("Stop")
        >>> embed = formatter(event_data, session_id)
    """
    
    def __init__(self) -> None:
        """Initialize registry with default formatters."""
        self._formatters: dict[str, EventFormatter] = {
            EventTypes.PRE_TOOL_USE.value: cast(EventFormatter, format_pre_tool_use),
            EventTypes.POST_TOOL_USE.value: cast(EventFormatter, format_post_tool_use),
            EventTypes.NOTIFICATION.value: cast(EventFormatter, format_notification),
            EventTypes.STOP.value: cast(EventFormatter, format_stop),
            EventTypes.SUBAGENT_STOP.value: cast(EventFormatter, format_subagent_stop),
        }
    
    def get_formatter(self, event_type: str) -> EventFormatter:
        """Get formatter for event type.
        
        Args:
            event_type: The type of event to get formatter for
            
        Returns:
            Formatter function that takes EventData and session_id and returns DiscordEmbed
        """
        if event_type in self._formatters:
            return self._formatters[event_type]
        # Return a default formatter for unknown events
        return _create_default_formatter(event_type)
    
    def register(self, event_type: str, formatter: EventFormatter) -> None:
        """Register a new formatter.
        
        Args:
            event_type: The event type to register formatter for
            formatter: The formatter function
        """
        self._formatters[event_type] = formatter


# Export all public items
__all__ = ['FormatterRegistry']