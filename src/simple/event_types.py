#!/usr/bin/env python3
"""Simple, beautiful type definitions for Discord Event Notifier.

This module provides clean type definitions for the simplified architecture,
focusing on clarity and ease of use.
"""

from typing import Any, Literal, ReadOnly, TypedDict

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


# =============================================================================
# Configuration Types
# =============================================================================

class Config(TypedDict, total=False):
    """Configuration dictionary structure."""
    
    # Discord connection
    webhook_url: str
    bot_token: str
    channel_id: str
    
    # Features
    use_threads: bool
    mention_user_id: str
    debug: bool
    
    # Filtering
    enabled_events: list[str]
    disabled_events: list[str]
    enabled_tools: list[str]
    disabled_tools: list[str]


# =============================================================================
# Handler Types  
# =============================================================================

# Event type literal for handler registry
EventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]

# Handler function signature
from typing import Callable, Optional
HandlerFunction = Callable[[EventData, Config], Optional[DiscordMessage]]