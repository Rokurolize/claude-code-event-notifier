"""Central type aliases for the discord notifier project.

This module defines common type aliases used throughout the codebase
to improve type safety and reduce mypy errors.
"""

from typing import NotRequired, TypedDict, Union

from src.utils.astolfo_logger import AstolfoLogger

# Initialize logger for module
_logger = AstolfoLogger(__name__)
_logger.debug("Loading type aliases module")

# JSON Primitive Types
type JSONPrimitive = Union[str, int, float, bool, None]
type JSONValue = Union[JSONPrimitive, dict[str, "JSONValue"], list["JSONValue"]]
type JSONDict = dict[str, JSONValue]
type JSONList = list[JSONValue]

# Discord API Types
type DiscordEmbed = dict[str, Union[str, int, list[dict[str, Union[str, bool]]]]]
type DiscordMessage = dict[str, Union[str, list[DiscordEmbed], None]]
type DiscordThread = dict[str, Union[str, int, bool, dict[str, Union[bool, int]]]]
type DiscordChannel = dict[str, Union[str, int]]
type DiscordWebhookPayload = DiscordMessage

# Event Data Types
type EventData = dict[str, Union[str, int, float, bool, dict[str, Union[str, int, float, bool]]]]
type ToolData = dict[str, Union[str, int, float, bool, list[str], dict[str, str]]]
type FormatterResult = DiscordEmbed

# Configuration Types
type ConfigDict = dict[str, Union[str, int, bool, list[str], None]]
type FilterConfig = dict[str, bool]
type ThreadConfig = dict[str, Union[str, bool, int]]

# HTTP Response Types
type HTTPResponse = dict[str, Union[str, int, dict[str, str]]]
type HTTPHeaders = dict[str, str]

# Session Types
type SessionData = dict[str, Union[str, int, float, list[str]]]
type SessionMetadata = dict[str, Union[str, int, float]]

# Thread Storage Types
type ThreadRecord = dict[str, Union[str, int]]
type ThreadMetadata = dict[str, Union[str, int, bool]]

# Logger Types
type LogRecord = dict[str, Union[str, int, float, bool, None]]
type LogContext = dict[str, Union[str, int, float, bool, list[str]]]

# Formatter Types
type EmbedField = dict[str, Union[str, bool]]
type EmbedAuthor = dict[str, str]
type EmbedFooter = dict[str, str]

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
    arguments: dict[str, Union[str, int, float, bool, list[str], dict[str, str]]]
    result: ToolResult
    message: str
    params: dict[str, Union[str, int, float, bool, list[str]]]

# Discord Embed Structure
class DiscordEmbedTyped(TypedDict, total=False):
    """Typed Discord embed structure."""
    title: str
    description: str
    color: int
    fields: list[EmbedField]
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
    enabled_events: list[str]
    disabled_events: list[str]
    mention_user_id: str
    debug: bool
    thread_name_prefix: str
    thread_auto_archive_duration: int
    max_retries: int
    retry_delay: float
