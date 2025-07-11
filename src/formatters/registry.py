"""Formatter registry for event type to formatter mapping.

This module provides a registry pattern for managing event formatters,
allowing dynamic registration and lookup of formatters by event type.
"""

from collections.abc import Callable

# Try to import types
try:
    from src.type_defs.events import EventData
    from src.type_defs.discord import DiscordEmbed, DiscordMessage
    from src.type_defs.config import Config
except ImportError:
    # Fallback if modules not available
    from discord_notifier import EventData, DiscordEmbed, DiscordMessage, Config  # type: ignore

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
        format_default_event,
    )
except ImportError:
    # These will be provided by discord_notifier
    from discord_notifier import (  # type: ignore
        format_pre_tool_use,
        format_post_tool_use,
        format_notification,
        format_stop,
        format_subagent_stop,
        format_default_event,
    )


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
            Formatter function that takes EventData and session_id and returns DiscordEmbed
        """
        if event_type in self._formatters:
            return self._formatters[event_type]
        # Return a lambda that captures the event_type for unknown events
        return lambda event_data, session_id: format_default_event(event_type, event_data, session_id)
    
    def register(self, event_type: str, formatter: Callable[[EventData, str], DiscordEmbed]) -> None:
        """Register a new formatter.
        
        Args:
            event_type: The event type to register formatter for
            formatter: The formatter function
        """
        self._formatters[event_type] = formatter


# Export all public items
__all__ = ['FormatterRegistry']