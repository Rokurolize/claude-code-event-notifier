"""Central type aliases for the discord notifier project.

This module defines common type aliases used throughout the codebase
to improve type safety and reduce mypy errors.
"""

from typing import Dict, List, Optional, Union, TypedDict, NotRequired
from typing_extensions import TypeAlias

# JSON Primitive Types
JSONPrimitive: TypeAlias = Union[str, int, float, bool, None]
JSONValue: TypeAlias = Union[JSONPrimitive, Dict[str, "JSONValue"], List["JSONValue"]]
JSONDict: TypeAlias = Dict[str, JSONValue]
JSONList: TypeAlias = List[JSONValue]

# Discord API Types
DiscordEmbed: TypeAlias = Dict[str, Union[str, int, List[Dict[str, Union[str, bool]]]]]
DiscordMessage: TypeAlias = Dict[str, Union[str, List[DiscordEmbed], None]]
DiscordThread: TypeAlias = Dict[str, Union[str, int, bool, Dict[str, Union[bool, int]]]]
DiscordChannel: TypeAlias = Dict[str, Union[str, int]]
DiscordWebhookPayload: TypeAlias = DiscordMessage

# Event Data Types
EventData: TypeAlias = Dict[str, Union[str, int, float, bool, Dict[str, Union[str, int, float, bool]]]]
ToolData: TypeAlias = Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
FormatterResult: TypeAlias = DiscordEmbed

# Configuration Types
ConfigDict: TypeAlias = Dict[str, Union[str, int, bool, List[str], None]]
FilterConfig: TypeAlias = Dict[str, bool]
ThreadConfig: TypeAlias = Dict[str, Union[str, bool, int]]

# HTTP Response Types
HTTPResponse: TypeAlias = Dict[str, Union[str, int, Dict[str, str]]]
HTTPHeaders: TypeAlias = Dict[str, str]

# Session Types
SessionData: TypeAlias = Dict[str, Union[str, int, float, List[str]]]
SessionMetadata: TypeAlias = Dict[str, Union[str, int, float]]

# Thread Storage Types
ThreadRecord: TypeAlias = Dict[str, Union[str, int]]
ThreadMetadata: TypeAlias = Dict[str, Union[str, int, bool]]

# Logger Types
LogRecord: TypeAlias = Dict[str, Union[str, int, float, bool, None]]
LogContext: TypeAlias = Dict[str, Union[str, int, float, bool, List[str]]]

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
    arguments: Dict[str, Union[str, int, float, bool, List[str], Dict[str, str]]]
    result: ToolResult
    message: str
    params: Dict[str, Union[str, int, float, bool, List[str]]]

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