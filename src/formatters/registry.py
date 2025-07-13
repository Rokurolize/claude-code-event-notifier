"""Formatter registry for event type to formatter mapping.

This module provides a registry pattern for managing event formatters,
allowing dynamic registration and lookup of formatters by event type.
"""

from typing import Protocol, cast

# Try to import logger
try:
    from src.utils.astolfo_logger import AstolfoLogger
except ImportError:
    # Create a no-op logger if import fails
    class AstolfoLogger:  # type: ignore
        def __init__(self, name: str) -> None: pass
        def info(self, msg: str, **kwargs: str | int | list[str]) -> None: pass
        def debug(self, msg: str, **kwargs: str | int | list[str]) -> None: pass
        def warning(self, msg: str, **kwargs: str | int | list[str]) -> None: pass
        def error(self, msg: str, **kwargs: str | int | list[str]) -> None: pass

# Try to import types
try:
    from src.type_defs.config import Config
    from src.type_defs.discord import DiscordEmbed, DiscordMessage
    from src.type_defs.events import (
        EventData,
        NotificationEventData,
        PostToolUseEventData,
        PreToolUseEventData,
        StopEventData,
        SubagentStopEventData,
    )
except ImportError:
    # Fallback if modules not available
    from discord_notifier import (  # type: ignore
        DiscordEmbed,
        EventData,
    )

# Try to import constants
try:
    from src.constants import EventTypes
except ImportError:
    from discord_notifier import EventTypes  # type: ignore

# Try to import formatters
try:
    from src.formatters.event_formatters import (
        format_default,
        format_notification,
        format_post_tool_use,
        format_pre_tool_use,
        format_stop,
        format_subagent_stop,
    )
except ImportError:
    # These will be provided by discord_notifier
    from discord_notifier import (  # type: ignore
        format_default,
        format_notification,
        format_post_tool_use,
        format_pre_tool_use,
        format_stop,
        format_subagent_stop,
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
    logger = AstolfoLogger("formatter_registry")
    logger.debug(
        "Creating default formatter for unknown event type",
        event_type=event_type
    )

    def formatter(event_data: EventData, session_id: str) -> DiscordEmbed:
        # Cast to dict for format_default which expects dict type
        data_dict = cast("dict[str, str | int | float | bool]", event_data)
        return cast("DiscordEmbed", format_default(data_dict, session_id))

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
        self._logger = AstolfoLogger("formatter_registry")
        self._formatters: dict[str, EventFormatter] = {
            EventTypes.PRE_TOOL_USE.value: cast("EventFormatter", format_pre_tool_use),
            EventTypes.POST_TOOL_USE.value: cast("EventFormatter", format_post_tool_use),
            EventTypes.NOTIFICATION.value: cast("EventFormatter", format_notification),
            EventTypes.STOP.value: cast("EventFormatter", format_stop),
            EventTypes.SUBAGENT_STOP.value: cast("EventFormatter", format_subagent_stop),
        }
        self._logger.info(
            "Formatter registry initialized",
            registered_formatters=list(self._formatters.keys())
        )

    def get_formatter(self, event_type: str) -> EventFormatter:
        """Get formatter for event type.

        Args:
            event_type: The type of event to get formatter for

        Returns:
            Formatter function that takes EventData and session_id and returns DiscordEmbed
        """
        if event_type in self._formatters:
            self._logger.debug(
                "Found registered formatter",
                event_type=event_type
            )
            return self._formatters[event_type]
        # Return a default formatter for unknown events
        self._logger.warning(
            "No formatter found for event type, using default",
            event_type=event_type,
            registered_types=list(self._formatters.keys())
        )
        return _create_default_formatter(event_type)

    def register(self, event_type: str, formatter: EventFormatter) -> None:
        """Register a new formatter.

        Args:
            event_type: The event type to register formatter for
            formatter: The formatter function
        """
        is_overwrite = event_type in self._formatters
        self._formatters[event_type] = formatter

        if is_overwrite:
            self._logger.warning(
                "Overwrote existing formatter",
                event_type=event_type,
                formatter_function=getattr(formatter, "__name__", str(formatter))
            )
        else:
            self._logger.info(
                "Registered new formatter",
                event_type=event_type,
                formatter_function=getattr(formatter, "__name__", str(formatter)),
                total_formatters=len(self._formatters)
            )


# Export all public items
__all__ = ["FormatterRegistry"]
