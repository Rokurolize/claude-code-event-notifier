#!/usr/bin/env python3
"""Simple, beautiful type definitions for Discord Event Notifier.

This module provides clean type definitions for the simplified architecture,
focusing on clarity and ease of use.
"""

from collections.abc import Callable
from typing import Any, Literal, TypedDict

# Python 3.14+ required - pure standard library, zero dependencies

# =============================================================================
# Core Event Types
# =============================================================================


class EventData(TypedDict, total=False):
    """Common structure for all Claude Code hook events."""

    session_id: str
    transcript_path: str
    hook_event_name: str
    # Additional fields vary by event type


class PreToolUseEvent(EventData):
    """PreToolUse event structure."""

    hook_event_name: Literal["PreToolUse"]
    tool_name: str
    tool_input: dict[str, Any]


class PostToolUseEvent(EventData):
    """PostToolUse event structure."""

    hook_event_name: Literal["PostToolUse"]
    tool_name: str
    tool_input: dict[str, Any]
    tool_response: dict[str, Any]


class NotificationEvent(EventData):
    """Notification event structure."""

    hook_event_name: Literal["Notification"]
    message: str


class StopEvent(EventData):
    """Stop event structure."""

    hook_event_name: Literal["Stop"]
    stop_hook_active: bool


class SubagentStopEvent(EventData):
    """SubagentStop event structure."""

    hook_event_name: Literal["SubagentStop"]
    stop_hook_active: bool


# =============================================================================
# Discord Message Types
# =============================================================================


class DiscordEmbed(TypedDict, total=False):
    """Discord embed structure."""

    title: str
    description: str
    color: int
    timestamp: str
    footer: dict[str, str]


class DiscordMessage(TypedDict, total=False):
    """Complete Discord message structure."""

    content: str  # Optional text content
    embeds: list[DiscordEmbed]  # Optional embeds


class RoutedMessage(TypedDict, total=False):
    """Discord message with routing information."""

    message: DiscordMessage
    channel_key: str  # Key for channel routing (e.g., "tool_activity", "completion")
    channel_id: str | None  # Resolved channel ID (optional override)


# =============================================================================
# Configuration Types
# =============================================================================


class ChannelMapping(TypedDict, total=False):
    """Channel mapping configuration."""

    # Basic channel categories (Phase 1)
    tool_activity: str  # PreToolUse/PostToolUse
    completion: str  # Stop/SubagentStop
    alerts: str  # Errors/warnings
    default: str  # Fallback channel

    # Detailed channels (Phase 2)
    bash_commands: str  # Bash tool
    file_operations: str  # Read/Edit/Write tools
    search_grep: str  # Grep/search tools
    ai_interactions: str  # Task/LLM tools
    system_notices: str  # System notifications


class ChannelRouting(TypedDict, total=False):
    """Channel routing configuration."""

    enabled: bool
    channels: ChannelMapping
    event_routing: dict[str, str]  # event_name -> channel_key
    tool_routing: dict[str, str]  # tool_name -> channel_key


class Config(TypedDict, total=False):
    """Configuration dictionary structure."""

    # Discord connection
    webhook_url: str
    bot_token: str
    channel_id: str

    # Features
    use_threads: bool
    thread_for_task: bool
    mention_user_id: str
    debug: bool

    # Filtering
    enabled_events: list[str]
    disabled_events: list[str]
    enabled_tools: list[str]
    disabled_tools: list[str]

    # New granular control
    event_states: dict[str, bool]
    tool_states: dict[str, bool]

    # Channel routing (new)
    channel_routing: ChannelRouting


# =============================================================================
# Handler Types
# =============================================================================

# Event type literal for handler registry
EventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]

# Handler function signature
HandlerFunction = Callable[[EventData, Config], DiscordMessage | RoutedMessage | None]
