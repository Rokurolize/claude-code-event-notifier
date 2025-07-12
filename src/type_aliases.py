"""Central type aliases for the discord notifier project.

This module defines common type aliases used throughout the codebase
to improve type safety and reduce mypy errors.
"""

from typing import Any, Dict, List, Optional, Union, TypedDict, NotRequired
from typing_extensions import TypeAlias

# Discord API Types
DiscordEmbed: TypeAlias = Dict[str, Any]
DiscordMessage: TypeAlias = Dict[str, Any]
DiscordThread: TypeAlias = Dict[str, Any]
DiscordChannel: TypeAlias = Dict[str, Any]
DiscordWebhookPayload: TypeAlias = Dict[str, Any]

# Event Data Types
EventData: TypeAlias = Dict[str, Any]
ToolData: TypeAlias = Dict[str, Any]
FormatterResult: TypeAlias = Dict[str, Any]

# Configuration Types
ConfigDict: TypeAlias = Dict[str, Any]
FilterConfig: TypeAlias = Dict[str, bool]
ThreadConfig: TypeAlias = Dict[str, Union[str, bool, int]]

# HTTP Response Types
HTTPResponse: TypeAlias = Dict[str, Any]
HTTPHeaders: TypeAlias = Dict[str, str]

# JSON Types
JSONValue: TypeAlias = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONDict: TypeAlias = Dict[str, JSONValue]

# Session Types
SessionData: TypeAlias = Dict[str, Any]
SessionMetadata: TypeAlias = Dict[str, Union[str, int, float]]

# Thread Storage Types
ThreadRecord: TypeAlias = Dict[str, Union[str, int]]
ThreadMetadata: TypeAlias = Dict[str, Any]

# Logger Types
LogRecord: TypeAlias = Dict[str, Any]
LogContext: TypeAlias = Dict[str, Any]

# Formatter Types
EmbedField: TypeAlias = Dict[str, Union[str, bool]]
EmbedAuthor: TypeAlias = Dict[str, str]
EmbedFooter: TypeAlias = Dict[str, str]

# Tool Result Types
class ToolResult(TypedDict):
    """Type for tool execution results."""
    output: NotRequired[str]
    error: NotRequired[str]
    exit_code: NotRequired[int]
    timeout: NotRequired[bool]

# Event Type Definitions
class EventDataTyped(TypedDict, total=False):
    """Typed event data structure."""
    event_type: str
    session_id: str
    timestamp: str
    tool: str
    arguments: Dict[str, Any]
    result: ToolResult
    message: str
    params: Dict[str, Any]

# Discord Embed Structure
class DiscordEmbedTyped(TypedDict, total=False):
    """Typed Discord embed structure."""
    title: str
    description: str
    color: int
    fields: List[EmbedField]
    author: EmbedAuthor
    footer: EmbedFooter
    timestamp: str
    url: str

# Configuration Structure
class ConfigTyped(TypedDict, total=False):
    """Typed configuration structure."""
    webhook_url: str
    bot_token: str
    channel_id: str
    use_threads: bool
    enabled_events: List[str]
    disabled_events: List[str]
    mention_user_id: str
    debug: bool
    thread_name_prefix: str
    thread_auto_archive_duration: int
    max_retries: int
    retry_delay: float