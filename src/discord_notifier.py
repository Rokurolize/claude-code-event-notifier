#!/usr/bin/env python3
"""
Claude Code Discord Notifier - Comprehensive event notification system.

This module provides a complete Discord notification system for Claude Code hook events.
It processes events from stdin, formats them into rich Discord embeds, and sends them
via webhook or bot API with support for threads and user mentions.

Key Features:
    - Zero external dependencies (Python standard library only)
    - Hierarchical TypedDict type system for type safety
    - Comprehensive event formatting with tool-specific details
    - Thread support for session organization
    - User mention system for important notifications
    - Robust error handling and graceful degradation
    - Debug logging with file output

Architecture:
    The module uses a pipeline architecture:
    1. Configuration loading with environment override precedence
    2. Event data validation using TypedDict hierarchies
    3. Tool-specific formatting via registry pattern
    4. HTTP client with retry logic and error handling
    5. Thread management with session caching

Usage:
    This module is designed to be called by Claude Code's hook system:
    
    $ CLAUDE_HOOK_EVENT=PreToolUse python3 discord_notifier.py < event.json
    
    Configuration is loaded from:
    1. Environment variables (highest priority)
    2. ~/.claude/hooks/.env.discord file
    3. Built-in defaults

Type System:
    The module uses extensive TypedDict hierarchies for type safety:
    - BaseField: Common properties across all types
    - TimestampedField: Fields with timestamp support
    - SessionAware: Session-aware fields
    - Tool-specific input/output types
    - Event data structures with validation

Error Handling:
    Custom exception hierarchy provides specific error types:
    - ConfigurationError: Configuration issues
    - DiscordAPIError: Discord API failures
    - EventProcessingError: Event processing issues
    - InvalidEventTypeError: Invalid event types

Thread Safety:
    The module maintains thread-safe session caching using a global dictionary.
    Each session gets a unique thread ID that persists for the session duration.

Authors:
    Claude Code Team
    
Version:
    2.0.0 - Enhanced with comprehensive type system and thread support
"""

import json
import logging
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    TypedDict,
    Literal,
    Protocol,
    Final,
    cast,
    Optional,
    Union,
)
from collections.abc import Callable

try:
    from typing import TypeGuard, NotRequired  # type: ignore[attr-defined]
except (ImportError, AttributeError):
    from typing_extensions import TypeGuard, NotRequired
from enum import Enum
from dataclasses import dataclass


# Custom exceptions
class DiscordNotifierError(Exception):
    """Base exception for Discord notifier.
    
    This is the root exception class for all Discord notifier-related errors.
    It provides a common base for exception handling and allows catching all
    notifier-specific errors with a single except clause.
    
    Usage:
        try:
            # Discord notifier operations
            pass
        except DiscordNotifierError as e:
            logger.error(f"Discord notifier error: {e}")
    """

    pass


class ConfigurationError(DiscordNotifierError):
    """Configuration related errors.
    
    Raised when there are issues with configuration loading, validation,
    or when required configuration values are missing or invalid.
    
    Common causes:
        - Missing webhook URL or bot credentials
        - Invalid Discord user IDs for mentions
        - Malformed .env.discord file
        - Thread configuration inconsistencies
    
    Args:
        message: Descriptive error message
        
    Example:
        >>> if not config.get('webhook_url'):
        ...     raise ConfigurationError("No webhook URL configured")
    """

    pass


class DiscordAPIError(DiscordNotifierError):
    """Discord API related errors.
    
    Raised when Discord API calls fail, including HTTP errors, network issues,
    or API response validation failures.
    
    Common causes:
        - Invalid webhook URL or bot token
        - Network connectivity issues
        - Discord API rate limiting
        - Invalid channel IDs or permissions
        - Thread creation failures
    
    Args:
        message: Descriptive error message including HTTP status if available
        
    Example:
        >>> try:
        ...     response = urllib.request.urlopen(request)
        ... except urllib.error.HTTPError as e:
        ...     raise DiscordAPIError(f"HTTP {e.code}: {e.reason}")
    """

    pass


class EventProcessingError(DiscordNotifierError):
    """Event processing related errors.
    
    Raised when there are issues processing Claude Code events, including
    JSON parsing errors, missing required fields, or formatting failures.
    
    Common causes:
        - Malformed JSON input from stdin
        - Missing required event fields
        - Invalid event data structure
        - Event formatting failures
    
    Args:
        message: Descriptive error message
        
    Example:
        >>> try:
        ...     event_data = json.loads(stdin_input)
        ... except json.JSONDecodeError as e:
        ...     raise EventProcessingError(f"Invalid JSON: {e}")
    """

    pass


class InvalidEventTypeError(EventProcessingError):
    """Invalid event type error.
    
    Raised when an unsupported or invalid event type is encountered.
    While the system handles unknown event types gracefully, this error
    can be used for strict validation scenarios.
    
    Common causes:
        - Typos in CLAUDE_HOOK_EVENT environment variable
        - New event types not yet supported
        - Corrupted event data
    
    Args:
        message: Descriptive error message including the invalid event type
        
    Example:
        >>> event_type = os.environ.get('CLAUDE_HOOK_EVENT')
        >>> if event_type and not is_valid_event_type(event_type):
        ...     raise InvalidEventTypeError(f"Unknown event type: {event_type}")
    """

    pass


# ==============================================================================
# TYPE DEFINITIONS: HIERARCHICAL TYPEDDICT STRUCTURE
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. BASE FOUNDATION TYPES
# ------------------------------------------------------------------------------

class BaseField(TypedDict):
    """Base field structure for common properties.
    
    This is the root of the TypedDict hierarchy, providing a common base
    for all field types in the system. It serves as a foundation for
    composition and inheritance patterns.
    
    Usage:
        This class is primarily used as a base for other TypedDict classes
        and should not be instantiated directly.
        
    Type Safety:
        Being a TypedDict, this provides compile-time type checking when
        used with type checkers like mypy or pyright.
    """
    pass


class TimestampedField(BaseField):
    """Fields that include timestamps.
    
    Extends BaseField to add optional timestamp support. Timestamps are
    stored as ISO format strings and are used for Discord embed metadata.
    
    Attributes:
        timestamp: Optional ISO format timestamp string (e.g., "2023-12-07T10:30:00Z")
        
    Usage:
        class MyEventData(TimestampedField):
            event_type: str
            
        data: MyEventData = {
            "event_type": "test",
            "timestamp": datetime.now().isoformat()
        }
    """
    timestamp: NotRequired[str]


class SessionAware(BaseField):
    """Fields that are session-aware.
    
    Extends BaseField to add session tracking capabilities. All Claude Code
    events are associated with a session, which is used for thread management
    and event correlation.
    
    Attributes:
        session_id: Unique identifier for the Claude Code session
        
    Usage:
        Session IDs are typically generated by Claude Code and passed in
        event data. They are used for:
        - Thread creation and management
        - Event correlation
        - Session-specific caching
        
    Example:
        >>> session_data: SessionAware = {"session_id": "abc123def456"}
        >>> thread_name = f"Session {session_data['session_id'][:8]}"
    """
    session_id: str


class PathAware(BaseField):
    """Fields that include file paths.
    
    Extends BaseField to add file path support. Used by tool inputs that
    operate on files, providing a consistent way to handle file paths
    across different tool types.
    
    Attributes:
        file_path: Optional absolute or relative file path
        
    Usage:
        File paths are automatically formatted for display using the
        format_file_path() utility function, which attempts to show
        relative paths when possible.
        
    Example:
        >>> file_data: PathAware = {
        ...     "file_path": "/home/user/project/src/main.py"
        ... }
        >>> display_path = format_file_path(file_data["file_path"])
    """
    file_path: NotRequired[str]


# ------------------------------------------------------------------------------
# 2. DISCORD API TYPES HIERARCHY
# ------------------------------------------------------------------------------

class DiscordFooter(TypedDict):
    """Discord footer structure.
    
    Represents the footer section of a Discord embed. Footers appear at the
    bottom of embeds and typically contain metadata or contextual information.
    
    Attributes:
        text: Footer text content (max 2048 characters per Discord API)
        
    Usage:
        Footers are used to display session information and event metadata:
        
        >>> footer: DiscordFooter = {
        ...     "text": "Session: abc123de | Event: PreToolUse"
        ... }
    """
    text: str


class DiscordFieldBase(TypedDict):
    """Base Discord field structure.
    
    Represents the basic structure of a Discord embed field. Fields are
    key-value pairs that appear in the embed body and provide structured
    information display.
    
    Attributes:
        name: Field name/label (max 256 characters per Discord API)
        value: Field value/content (max 1024 characters per Discord API)
        
    Usage:
        This is the base class for Discord fields. Use DiscordField for
        full functionality including inline support.
        
    Example:
        >>> field_base: DiscordFieldBase = {
        ...     "name": "Command",
        ...     "value": "git status"
        ... }
    """
    name: str
    value: str


class DiscordField(DiscordFieldBase):
    """Discord field with optional inline support.
    
    Extends DiscordFieldBase to add inline positioning support. Inline fields
    appear side-by-side in the embed, allowing for more compact layouts.
    
    Attributes:
        name: Field name/label (inherited from DiscordFieldBase)
        value: Field value/content (inherited from DiscordFieldBase)
        inline: Optional boolean to display field inline (default: False)
        
    Usage:
        >>> field: DiscordField = {
        ...     "name": "Status",
        ...     "value": "Success",
        ...     "inline": True
        ... }
        
    Layout:
        - inline=True: Fields appear side-by-side (up to 3 per row)
        - inline=False: Fields appear stacked vertically
    """
    inline: NotRequired[bool]


class DiscordEmbedBase(TypedDict):
    """Base Discord embed structure."""
    title: NotRequired[str]
    description: NotRequired[str]
    color: NotRequired[int]


class DiscordEmbed(DiscordEmbedBase, TimestampedField):
    """Complete Discord embed structure."""
    footer: NotRequired[DiscordFooter]
    fields: NotRequired[list[DiscordField]]


class DiscordMessageBase(TypedDict):
    """Base Discord message structure."""
    embeds: NotRequired[list[DiscordEmbed]]


class DiscordMessage(DiscordMessageBase):
    """Discord message with optional content."""
    content: NotRequired[str]  # For mentions


class DiscordThreadMessage(DiscordMessageBase):
    """Discord message with thread support."""
    thread_name: NotRequired[str]  # For creating new threads


# ------------------------------------------------------------------------------
# 3. CONFIGURATION HIERARCHY
# ------------------------------------------------------------------------------

class DiscordCredentials(TypedDict):
    """Discord authentication credentials."""
    webhook_url: Optional[str]
    bot_token: Optional[str]
    channel_id: Optional[str]


class ThreadConfiguration(TypedDict):
    """Thread-specific configuration."""
    use_threads: bool
    channel_type: Literal["text", "forum"]
    thread_prefix: str


class NotificationConfiguration(TypedDict):
    """Notification-specific configuration."""
    mention_user_id: Optional[str]
    debug: bool


class EventFilterConfiguration(TypedDict):
    """Event filtering configuration."""
    enabled_events: Optional[list[str]]
    disabled_events: Optional[list[str]]


class Config(DiscordCredentials, ThreadConfiguration, NotificationConfiguration, EventFilterConfiguration):
    """Complete configuration combining all aspects."""
    pass


# ------------------------------------------------------------------------------
# 4. TOOL INPUT HIERARCHY
# ------------------------------------------------------------------------------

class ToolInputBase(TypedDict):
    """Base tool input structure."""
    description: NotRequired[str]


class BashToolInput(ToolInputBase):
    """Bash tool input structure."""
    command: str


class FileEditOperation(TypedDict):
    """Individual file edit operation."""
    old_string: str
    new_string: str
    replace_all: NotRequired[bool]


class FileToolInputBase(ToolInputBase, PathAware):
    """Base file tool input structure."""
    pass


class ReadToolInput(FileToolInputBase):
    """Read tool input structure."""
    offset: NotRequired[int]
    limit: NotRequired[int]


class WriteToolInput(FileToolInputBase):
    """Write tool input structure."""
    content: str


class EditToolInput(FileToolInputBase):
    """Edit tool input structure."""
    old_string: str
    new_string: str
    replace_all: NotRequired[bool]


class MultiEditToolInput(FileToolInputBase):
    """Multi-edit tool input structure."""
    edits: list[FileEditOperation]


class ListToolInput(ToolInputBase, PathAware):
    """List tool input structure."""
    ignore: NotRequired[list[str]]


class SearchToolInputBase(ToolInputBase):
    """Base search tool input structure."""
    pattern: str
    path: NotRequired[str]


class GlobToolInput(SearchToolInputBase):
    """Glob tool input structure."""
    pass


class GrepToolInput(SearchToolInputBase):
    """Grep tool input structure."""
    include: NotRequired[str]


class TaskToolInput(ToolInputBase):
    """Task tool input structure."""
    prompt: str


class WebToolInput(ToolInputBase):
    """Web tool input structure."""
    url: str
    prompt: str


# Legacy FileToolInput for backward compatibility
class FileToolInput(TypedDict, total=False):
    """Legacy file operation tool input structure (for backward compatibility)."""
    file_path: str
    old_string: str
    new_string: str
    edits: list[FileEditOperation]
    offset: Optional[int]
    limit: Optional[int]


# Legacy SearchToolInput for backward compatibility
class SearchToolInput(TypedDict, total=False):
    """Legacy search tool input structure (for backward compatibility)."""
    pattern: str
    path: str
    include: str


# Union type for all tool inputs
ToolInput = Union[
    BashToolInput,
    ReadToolInput,
    WriteToolInput,
    EditToolInput,
    MultiEditToolInput,
    ListToolInput,
    GlobToolInput,
    GrepToolInput,
    TaskToolInput,
    WebToolInput,
    FileToolInput,  # Legacy compatibility
    SearchToolInput,  # Legacy compatibility
    dict[str, Any]
]


# ------------------------------------------------------------------------------
# 5. TOOL RESPONSE HIERARCHY
# ------------------------------------------------------------------------------

class ToolResponseBase(TypedDict):
    """Base tool response structure."""
    success: NotRequired[bool]
    error: NotRequired[str]


class BashToolResponse(ToolResponseBase):
    """Bash tool response structure."""
    stdout: str
    stderr: str
    interrupted: bool
    isImage: bool


class FileOperationResponse(ToolResponseBase):
    """File operation response structure."""
    filePath: NotRequired[str]


class SearchResponse(ToolResponseBase):
    """Search operation response structure."""
    results: NotRequired[list[str]]
    count: NotRequired[int]


# Union type for all tool responses
ToolResponse = Union[
    BashToolResponse,
    FileOperationResponse,
    SearchResponse,
    str,
    dict[str, Any],
    list[Any]
]


# ------------------------------------------------------------------------------
# 6. EVENT DATA HIERARCHY
# ------------------------------------------------------------------------------

class BaseEventData(SessionAware, TimestampedField):
    """Base event data structure."""
    transcript_path: NotRequired[str]
    hook_event_name: str


class ToolEventDataBase(BaseEventData):
    """Base tool event data structure."""
    tool_name: str
    tool_input: dict[str, Any]


class PreToolUseEventData(ToolEventDataBase):
    """PreToolUse event data structure."""
    pass


class PostToolUseEventData(ToolEventDataBase):
    """PostToolUse event data structure."""
    tool_response: ToolResponse


class NotificationEventData(BaseEventData):
    """Notification event data structure."""
    message: str
    title: NotRequired[str]
    level: NotRequired[Literal["info", "warning", "error"]]


class StopEventDataBase(BaseEventData):
    """Base stop event data structure."""
    stop_hook_active: NotRequired[bool]


class StopEventData(StopEventDataBase):
    """Stop event data structure."""
    duration: NotRequired[float]
    tools_used: NotRequired[int]
    messages_exchanged: NotRequired[int]


class SubagentStopEventData(StopEventData):
    """SubagentStop event data structure."""
    task_description: NotRequired[str]
    result: NotRequired[Union[str, dict[str, Any]]]
    execution_time: NotRequired[float]
    status: NotRequired[str]


# Union type for all event data
EventData = Union[
    PreToolUseEventData,
    PostToolUseEventData,
    NotificationEventData,
    StopEventData,
    SubagentStopEventData,
    dict[str, Any]
]

# ------------------------------------------------------------------------------
# 7. ENHANCED TYPE SAFETY FEATURES
# ------------------------------------------------------------------------------

# Type guard functions
def is_tool_event_data(data: dict[str, Any]) -> TypeGuard[ToolEventDataBase]:
    """Check if event data is tool-related."""
    return "tool_name" in data


def is_notification_event_data(data: dict[str, Any]) -> TypeGuard[NotificationEventData]:
    """Check if event data is notification-related."""
    return "message" in data


def is_stop_event_data(data: dict[str, Any]) -> TypeGuard[StopEventDataBase]:
    """Check if event data is stop-related."""
    return "hook_event_name" in data


def is_bash_tool_input(tool_input: dict[str, Any]) -> TypeGuard[BashToolInput]:
    """Check if tool input is for Bash tool."""
    return "command" in tool_input


def is_file_tool_input(tool_input: dict[str, Any]) -> TypeGuard[FileToolInputBase]:
    """Check if tool input is for file operations."""
    return "file_path" in tool_input


def is_search_tool_input(tool_input: dict[str, Any]) -> TypeGuard[SearchToolInputBase]:
    """Check if tool input is for search operations."""
    return "pattern" in tool_input


# Configuration validation
class ConfigValidator:
    """Validator for Config TypedDict.
    
    Provides static methods to validate different aspects of the Discord
    configuration. Used to ensure configuration consistency and completeness
    before attempting to send messages.
    
    Validation Areas:
        - Credentials: Webhook URL or bot token/channel ID combination
        - Thread configuration: Consistency between channel type and auth method
        - Mention configuration: Valid Discord user ID format
        
    Usage:
        >>> config = ConfigLoader.load()
        >>> if not ConfigValidator.validate_all(config):
        ...     raise ConfigurationError("Invalid configuration")
    """
    
    @staticmethod
    def validate_credentials(config: Config) -> bool:
        """Validate that at least one credential method is configured.
        
        Checks that either webhook URL or bot token/channel ID combination
        is available for Discord API access.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            bool: True if valid credentials are configured, False otherwise
            
        Validation Logic:
            - Webhook URL alone is sufficient for basic messaging
            - Bot token + channel ID combination is required for bot API
            - At least one method must be configured
            
        Example:
            >>> config = {"webhook_url": "https://discord.com/api/webhooks/..."}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token", "channel_id": "123"}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token"}  # Missing channel_id
            >>> ConfigValidator.validate_credentials(config)  # False
        """
        return bool(
            config.get("webhook_url") or 
            (config.get("bot_token") and config.get("channel_id"))
        )
    
    @staticmethod
    def validate_thread_config(config: Config) -> bool:
        """Validate thread configuration consistency.
        
        Ensures that thread configuration is consistent with available
        authentication methods and channel types.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            bool: True if thread configuration is valid, False otherwise
            
        Validation Rules:
            - If threads are disabled, configuration is always valid
            - Forum channels require webhook URL for thread creation
            - Text channels require bot token + channel ID for thread creation
            - Invalid channel types are rejected
            
        Thread Types:
            - Forum channels: Use webhook API with thread_name parameter
            - Text channels: Use bot API to create public threads
            
        Example:
            >>> # Valid forum channel config
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum",
            ...     "webhook_url": "https://discord.com/api/webhooks/..."
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # True
            
            >>> # Invalid: forum channel without webhook
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum",
            ...     "bot_token": "token"
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # False
        """
        if not config.get("use_threads", False):
            return True
        
        channel_type = cast(str, config.get("channel_type", "text"))
        if channel_type == "forum":
            return bool(config.get("webhook_url"))
        elif channel_type == "text":
            return bool(config.get("bot_token") and config.get("channel_id"))
        else:
            # Invalid channel type
            return False
    
    @staticmethod
    def validate_mention_config(config: Config) -> bool:
        """Validate mention configuration.
        
        Validates Discord user ID format for mention functionality.
        Discord user IDs are numeric strings with specific length requirements.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            bool: True if mention configuration is valid, False otherwise
            
        Validation Rules:
            - If no mention_user_id is configured, validation passes
            - Discord user IDs must be numeric strings
            - Discord user IDs must be at least 17 characters long
            - User IDs are typically 17-19 characters in length
            
        Discord User ID Format:
            - Numeric string (e.g., "123456789012345678")
            - Generated using Discord's snowflake algorithm
            - Unique across all Discord users
            
        Example:
            >>> # Valid user ID
            >>> config = {"mention_user_id": "123456789012345678"}
            >>> ConfigValidator.validate_mention_config(config)  # True
            
            >>> # Invalid: non-numeric
            >>> config = {"mention_user_id": "invalid_id"}
            >>> ConfigValidator.validate_mention_config(config)  # False
            
            >>> # Invalid: too short
            >>> config = {"mention_user_id": "12345"}
            >>> ConfigValidator.validate_mention_config(config)  # False
        """
        mention_user_id = config.get("mention_user_id")
        if mention_user_id:
            # Basic validation: Discord user IDs are numeric strings
            return mention_user_id.isdigit() and len(mention_user_id) >= 17
        return True
    
    @staticmethod
    def validate_all(config: Config) -> bool:
        """Validate all configuration aspects.
        
        Performs comprehensive validation of all configuration aspects,
        ensuring the configuration is complete and consistent.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            bool: True if all validation checks pass, False otherwise
            
        Validation Performed:
            1. Credentials validation (webhook URL or bot token/channel ID)
            2. Thread configuration consistency
            3. Mention configuration format
            
        Usage:
            This is the recommended method for validating configuration
            before using the Discord notifier.
            
        Example:
            >>> config = ConfigLoader.load()
            >>> if not ConfigValidator.validate_all(config):
            ...     raise ConfigurationError("Configuration validation failed")
            >>> # Safe to use config for Discord operations
            
        Failure Scenarios:
            - No authentication method configured
            - Thread configuration mismatch with auth method
            - Invalid Discord user ID format
            - Missing required fields for selected features
        """
        return (
            ConfigValidator.validate_credentials(config) and
            ConfigValidator.validate_thread_config(config) and
            ConfigValidator.validate_mention_config(config)
        )


# Event data validation
class EventDataValidator:
    """Validator for EventData structures."""
    
    @staticmethod
    def validate_base_event_data(data: dict[str, Any]) -> bool:
        """Validate base event data requirements."""
        required_fields = {"session_id", "hook_event_name"}
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_tool_event_data(data: dict[str, Any]) -> bool:
        """Validate tool event data requirements."""
        if not EventDataValidator.validate_base_event_data(data):
            return False
        
        required_fields = {"tool_name", "tool_input"}
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_notification_event_data(data: dict[str, Any]) -> bool:
        """Validate notification event data requirements."""
        if not EventDataValidator.validate_base_event_data(data):
            return False
        
        return "message" in data
    
    @staticmethod
    def validate_stop_event_data(data: dict[str, Any]) -> bool:
        """Validate stop event data requirements."""
        return EventDataValidator.validate_base_event_data(data)


# Tool input validation
class ToolInputValidator:
    """Validator for ToolInput structures."""
    
    @staticmethod
    def validate_bash_input(tool_input: dict[str, Any]) -> bool:
        """Validate Bash tool input."""
        return "command" in tool_input and isinstance(tool_input["command"], str)
    
    @staticmethod
    def validate_file_input(tool_input: dict[str, Any]) -> bool:
        """Validate file tool input."""
        return "file_path" in tool_input and isinstance(tool_input["file_path"], str)
    
    @staticmethod
    def validate_search_input(tool_input: dict[str, Any]) -> bool:
        """Validate search tool input."""
        return "pattern" in tool_input and isinstance(tool_input["pattern"], str)
    
    @staticmethod
    def validate_web_input(tool_input: dict[str, Any]) -> bool:
        """Validate web tool input."""
        return (
            "url" in tool_input and isinstance(tool_input["url"], str) and
            "prompt" in tool_input and isinstance(tool_input["prompt"], str)
        )


# ==============================================================================
# END OF TYPE DEFINITIONS
# ==============================================================================

# Type aliases for better code clarity
EventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]
ToolName = Literal[
    "Bash",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Glob",
    "Grep",
    "LS",
    "Task",
    "WebFetch",
]


# Constants and Enums
class ToolNames(str, Enum):
    """Tool name constants."""

    BASH = "Bash"
    READ = "Read"
    WRITE = "Write"
    EDIT = "Edit"
    MULTI_EDIT = "MultiEdit"
    GLOB = "Glob"
    GREP = "Grep"
    LS = "LS"
    TASK = "Task"
    WEB_FETCH = "WebFetch"


class EventTypes(str, Enum):
    """Event type constants."""

    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    NOTIFICATION = "Notification"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"


@dataclass(frozen=True)
class TruncationLimits:
    """Character limits for truncation."""

    COMMAND_PREVIEW: int = 100
    COMMAND_FULL: int = 500
    STRING_PREVIEW: int = 100
    PROMPT_PREVIEW: int = 200
    OUTPUT_PREVIEW: int = 500
    ERROR_PREVIEW: int = 300
    RESULT_PREVIEW: int = 300
    JSON_PREVIEW: int = 400


@dataclass(frozen=True)
class DiscordLimits:
    """Discord API limits."""

    MAX_TITLE_LENGTH: int = 256
    MAX_DESCRIPTION_LENGTH: int = 4096
    MAX_FIELD_VALUE_LENGTH: int = 1024
    MAX_EMBED_COUNT: int = 10


@dataclass(frozen=True)
class DiscordColors:
    """Discord embed colors."""

    BLUE: int = 0x3498DB
    GREEN: int = 0x2ECC71
    ORANGE: int = 0xF39C12
    GRAY: int = 0x95A5A6
    PURPLE: int = 0x9B59B6
    DEFAULT: int = 0x808080


# Event colors mapping
EVENT_COLORS: Final[dict[EventType, int]] = {
    "PreToolUse": DiscordColors.BLUE,
    "PostToolUse": DiscordColors.GREEN,
    "Notification": DiscordColors.ORANGE,
    "Stop": DiscordColors.GRAY,
    "SubagentStop": DiscordColors.PURPLE,
}

# Tool emojis mapping
TOOL_EMOJIS: Final[dict[str, str]] = {
    ToolNames.BASH.value: "🔧",
    ToolNames.READ.value: "📖",
    ToolNames.WRITE.value: "✏️",
    ToolNames.EDIT.value: "✂️",
    ToolNames.MULTI_EDIT.value: "📝",
    ToolNames.GLOB.value: "🔍",
    ToolNames.GREP.value: "🔎",
    ToolNames.LS.value: "📁",
    ToolNames.TASK.value: "🤖",
    ToolNames.WEB_FETCH.value: "🌐",
    "mcp__human-in-the-loop__ask_human": "💬",
}

# Environment variable keys
ENV_WEBHOOK_URL: Final[str] = "DISCORD_WEBHOOK_URL"
ENV_BOT_TOKEN: Final[str] = "DISCORD_TOKEN"
ENV_CHANNEL_ID: Final[str] = "DISCORD_CHANNEL_ID"
ENV_DEBUG: Final[str] = "DISCORD_DEBUG"
ENV_USE_THREADS: Final[str] = "DISCORD_USE_THREADS"
ENV_CHANNEL_TYPE: Final[str] = "DISCORD_CHANNEL_TYPE"
ENV_THREAD_PREFIX: Final[str] = "DISCORD_THREAD_PREFIX"
ENV_MENTION_USER_ID: Final[str] = "DISCORD_MENTION_USER_ID"
ENV_ENABLED_EVENTS: Final[str] = "DISCORD_ENABLED_EVENTS"
ENV_DISABLED_EVENTS: Final[str] = "DISCORD_DISABLED_EVENTS"
ENV_HOOK_EVENT: Final[str] = "CLAUDE_HOOK_EVENT"

# Other constants
USER_AGENT: Final[str] = "ClaudeCodeDiscordNotifier/1.0"
DEFAULT_TIMEOUT: Final[int] = 10
TRUNCATION_SUFFIX: Final[str] = "..."

# Thread management
SESSION_THREAD_CACHE: dict[str, str] = {}  # session_id -> thread_id mapping


# Type guards
def is_valid_event_type(event_type: str) -> TypeGuard[EventType]:
    """Check if event type is valid."""
    return event_type in {e.value for e in EventTypes}


def is_bash_tool(tool_name: str) -> bool:
    """Check if tool is Bash."""
    return tool_name == ToolNames.BASH.value


def is_file_tool(tool_name: str) -> bool:
    """Check if tool is a file operation tool."""
    return tool_name in {
        ToolNames.READ.value,
        ToolNames.WRITE.value,
        ToolNames.EDIT.value,
        ToolNames.MULTI_EDIT.value,
    }


def is_search_tool(tool_name: str) -> bool:
    """Check if tool is a search tool."""
    return tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value}


def is_list_tool(tool_name: str) -> bool:
    """Check if tool returns list results."""
    return tool_name in {ToolNames.GLOB.value, ToolNames.GREP.value, ToolNames.LS.value}


# Utility functions
def truncate_string(text: str, max_length: int, suffix: str = TRUNCATION_SUFFIX) -> str:
    """Truncate string to maximum length with suffix.
    
    Safely truncates text to fit within Discord's character limits while
    preserving readability by adding a truncation indicator.
    
    Args:
        text: The string to potentially truncate
        max_length: Maximum allowed length including suffix
        suffix: String to append when truncation occurs (default: "...")
        
    Returns:
        str: Original string if within limit, or truncated string with suffix
        
    Behavior:
        - If text is within limit, returns unchanged
        - If truncation needed, reserves space for suffix
        - Ensures result never exceeds max_length
        
    Example:
        >>> truncate_string("Hello world!", 10)
        'Hello w...'
        >>> truncate_string("Short", 10)
        'Short'
        >>> truncate_string("Long text here", 8, ">>")
        'Long t>>'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_file_path(file_path: str) -> str:
    """Format file path to be relative if possible.
    
    Converts absolute file paths to relative paths when possible to improve
    readability in Discord messages. Falls back to filename only if relative
    path conversion fails.
    
    Args:
        file_path: Absolute or relative file path to format
        
    Returns:
        str: Formatted path string, empty string if input is empty
        
    Formatting Logic:
        1. If empty path, return empty string
        2. Try to convert to relative path from current working directory
        3. If relative conversion fails, return just the filename
        4. If all else fails, return the original path
        
    Example:
        >>> # Assuming cwd is /home/user/project
        >>> format_file_path("/home/user/project/src/main.py")
        'src/main.py'
        >>> format_file_path("/etc/passwd")
        'passwd'
        >>> format_file_path("")
        ''
        
    Error Handling:
        - ValueError: Path is not relative to current directory
        - OSError: File system access issues
        - Both errors result in filename-only fallback
    """
    if not file_path:
        return ""

    path = Path(file_path)
    try:
        return str(path.relative_to(Path.cwd()))
    except (ValueError, OSError):
        return path.name


def parse_env_file(file_path: Path) -> dict[str, str]:
    """Parse environment file and return key-value pairs.
    
    Parses .env format files containing KEY=VALUE pairs, with support for
    comments and quoted values. Used to load Discord configuration from
    the ~/.claude/hooks/.env.discord file.
    
    Args:
        file_path: Path to the environment file to parse
        
    Returns:
        dict[str, str]: Dictionary mapping environment variable names to values
        
    Raises:
        ConfigurationError: If file cannot be read or parsed
        
    File Format:
        - KEY=VALUE pairs, one per line
        - Comments start with # and are ignored
        - Values can be quoted with single or double quotes
        - Quotes are stripped from values
        - Empty lines are ignored
        
    Example File Content:
        ```
        # Discord configuration
        DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123/abc
        DISCORD_TOKEN="your_bot_token_here"
        DISCORD_CHANNEL_ID='123456789012345678'
        # Thread settings
        DISCORD_USE_THREADS=1
        ```
        
    Example Usage:
        >>> env_vars = parse_env_file(Path(".env.discord"))
        >>> webhook_url = env_vars.get("DISCORD_WEBHOOK_URL")
        
    Error Handling:
        - IOError: File access issues (permissions, file not found)
        - ValueError: Line parsing issues (malformed KEY=VALUE pairs)
        - Both result in ConfigurationError being raised
    """
    env_vars: dict[str, str] = {}

    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    value = value.strip('"').strip("'")
                    env_vars[key] = value
    except (IOError, ValueError) as e:
        raise ConfigurationError(f"Error reading {file_path}: {e}")

    return env_vars


def parse_event_list(event_list_str: str) -> list[str]:
    """Parse comma-separated event list string into validated list.
    
    Parses environment variable values like "Stop,Notification" into a list
    of valid event type strings. Invalid event types are filtered out with
    debug logging.
    
    Args:
        event_list_str: Comma-separated string of event types
        
    Returns:
        list[str]: List of valid event type strings
        
    Example:
        >>> parse_event_list("Stop,Notification,InvalidEvent")
        ['Stop', 'Notification']
        >>> parse_event_list("")
        []
        >>> parse_event_list("  PreToolUse  ,  PostToolUse  ")
        ['PreToolUse', 'PostToolUse']
    """
    if not event_list_str:
        return []
    
    # Split and clean up event names
    events = [event.strip() for event in event_list_str.split(",")]
    valid_events = []
    
    # Filter to only valid event types
    for event in events:
        if event and is_valid_event_type(event):
            valid_events.append(event)
        elif event:  # Non-empty but invalid
            # Note: We can't access logger here, so invalid events are silently filtered
            # This maintains the principle of graceful degradation
            pass
    
    return valid_events


def should_process_event(event_type: str, config: Config) -> bool:
    """Determine if an event should be processed based on filtering configuration.
    
    Implements event filtering logic with the following precedence:
    1. If enabled_events is configured, only process events in that list
    2. If disabled_events is configured, skip events in that list
    3. If both are configured, enabled_events takes precedence
    4. If neither is configured, process all events (default behavior)
    
    Args:
        event_type: The event type to check (e.g., "Stop", "Notification")
        config: Configuration containing filtering settings
        
    Returns:
        bool: True if the event should be processed, False otherwise
        
    Examples:
        >>> config = {"enabled_events": ["Stop", "Notification"], "disabled_events": None}
        >>> should_process_event("Stop", config)
        True
        >>> should_process_event("PreToolUse", config)
        False
        >>> 
        >>> config = {"enabled_events": None, "disabled_events": ["PreToolUse"]}
        >>> should_process_event("PreToolUse", config)
        False
        >>> should_process_event("Stop", config)
        True
    """
    enabled_events = config.get("enabled_events")
    disabled_events = config.get("disabled_events")
    
    # If enabled_events is configured, only process events in that list
    if enabled_events:
        return event_type in enabled_events
    
    # If disabled_events is configured, skip events in that list
    if disabled_events:
        return event_type not in disabled_events
    
    # Default: process all events
    return True


def get_truncation_suffix(original_length: int, limit: int) -> str:
    """Get truncation suffix if text was truncated.
    
    Returns a formatted truncation indicator if the original text length
    exceeded the specified limit. Used to indicate when content has been
    shortened for display.
    
    Args:
        original_length: Length of the original text before truncation
        limit: Maximum length limit that was applied
        
    Returns:
        str: Formatted truncation suffix with space, or empty string if no truncation
        
    Usage:
        This function is used in formatting functions to indicate when
        content has been truncated for Discord display limits.
        
    Example:
        >>> get_truncation_suffix(150, 100)
        ' ...'
        >>> get_truncation_suffix(50, 100)
        ''
        >>> # Used in formatting:
        >>> original = "Very long text here"
        >>> truncated = truncate_string(original, 10)
        >>> suffix = get_truncation_suffix(len(original), 10)
        >>> display_text = f"{truncated}{suffix}"
    """
    return f" {TRUNCATION_SUFFIX}" if original_length > limit else ""


def add_field(
    desc_parts: list[str], label: str, value: str, code: bool = False
) -> None:
    """Add a field to description parts.
    
    Adds a formatted field to a list of description parts, with optional
    code formatting for technical content like file paths and commands.
    
    Args:
        desc_parts: List to append the formatted field to
        label: Field label/name (will be bolded)
        value: Field value/content
        code: Whether to format value as inline code (default: False)
        
    Returns:
        None: Modifies desc_parts list in place
        
    Formatting:
        - Label is always bolded with **label**
        - Value is either plain text or inline code with backticks
        - Code formatting is used for technical content (paths, commands)
        
    Example:
        >>> parts = []
        >>> add_field(parts, "Status", "Success")
        >>> add_field(parts, "Command", "git status", code=True)
        >>> parts
        ['**Status:** Success', '**Command:** `git status`']
        
    Usage:
        Primarily used in event formatting functions to build Discord
        embed descriptions with consistent field formatting.
    """
    if code:
        desc_parts.append(f"**{label}:** `{value}`")
    else:
        desc_parts.append(f"**{label}:** {value}")


def format_json_field(
    value: Any, label: str, limit: int = TruncationLimits.JSON_PREVIEW
) -> str:
    """Format a JSON value as a field.
    
    Formats complex data structures as JSON code blocks for Discord display.
    Handles truncation for large JSON objects while preserving readability.
    
    Args:
        value: Any JSON-serializable value to format
        label: Field label for the JSON block
        limit: Maximum character limit for JSON content
        
    Returns:
        str: Formatted JSON field with markdown code block
        
    Formatting:
        - JSON is formatted with 2-space indentation
        - Displayed in a ```json code block for syntax highlighting
        - Truncated if exceeds limit, with truncation indicator
        - Label is bolded and appears before the code block
        
    Example:
        >>> data = {"status": "success", "count": 42}
        >>> format_json_field(data, "Response", 100)
        '**Response:**\n```json\n{\n  "status": "success",\n  "count": 42\n}\n```'
        
    Usage:
        Used to display complex event data, tool inputs, and responses
        in a readable format within Discord embeds.
        
    Error Handling:
        - json.dumps() may raise TypeError for non-serializable objects
        - Non-serializable objects should be converted to strings first
    """
    value_str = json.dumps(value, indent=2)
    truncated = truncate_string(value_str, limit)
    suffix = get_truncation_suffix(len(value_str), limit)
    return f"**{label}:**\n```json\n{truncated}{suffix}\n```"


# HTTP Client
class HTTPClient:
    """HTTP client for Discord API calls."""

    def __init__(self, logger: logging.Logger, timeout: int = DEFAULT_TIMEOUT):
        self.logger = logger
        self.timeout = timeout
        self.headers_base = {"User-Agent": USER_AGENT}

    def post_webhook(self, url: str, data: DiscordMessage) -> bool:
        """Send message via Discord webhook."""
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
        }

        return self._make_request(url, data, headers, "Webhook", 204)

    def post_bot_api(self, url: str, data: DiscordMessage, token: str) -> bool:
        """Send message via Discord bot API."""
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        return self._make_request(
            url, data, headers, "Bot API", lambda s: 200 <= s < 300
        )

    def _make_request(
        self,
        url: str,
        data: DiscordMessage,
        headers: dict[str, str],
        api_name: str,
        success_check: Union[int, Callable[[int], bool]],
    ) -> bool:
        """Make HTTP request with error handling."""
        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status = response.status
                self.logger.debug(f"{api_name} response: {status}")

                if callable(success_check):
                    return bool(success_check(status))
                return bool(status == success_check)

        except urllib.error.HTTPError as e:
            self.logger.error(f"{api_name} HTTP error {e.code}: {e.reason}")
            raise DiscordAPIError(f"{api_name} failed: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            self.logger.error(f"{api_name} URL error: {e.reason}")
            raise DiscordAPIError(f"{api_name} connection failed: {e.reason}")
        except Exception as e:
            self.logger.error(f"{api_name} unexpected error: {type(e).__name__}: {e}")
            raise DiscordAPIError(f"{api_name} unexpected error: {e}")

    def post_webhook_to_thread(
        self, url: str, data: DiscordMessage, thread_id: str
    ) -> bool:
        """Send message to existing thread via Discord webhook."""
        thread_url = f"{url}?thread_id={thread_id}"
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
        }

        return self._make_request(thread_url, data, headers, "Webhook Thread", 204)

    def create_forum_thread(
        self, url: str, data: DiscordThreadMessage, thread_name: str
    ) -> Optional[str]:
        """Create new forum thread via Discord webhook. Returns thread_id if successful."""
        thread_data = {**data, "thread_name": thread_name}
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
        }

        try:
            json_data = json.dumps(thread_data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status = response.status
                self.logger.debug(f"Forum Thread Creation response: {status}")

                if status == 200:
                    # Parse response to get thread_id
                    response_data = json.loads(response.read().decode("utf-8"))
                    return cast(Optional[str], response_data.get("id"))  # thread_id
                return None

        except urllib.error.HTTPError as e:
            self.logger.error(f"Forum Thread Creation HTTP error {e.code}: {e.reason}")
            raise DiscordAPIError(f"Forum thread creation failed: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            self.logger.error(f"Forum Thread Creation URL error: {e.reason}")
            raise DiscordAPIError(
                f"Forum thread creation connection failed: {e.reason}"
            )
        except Exception as e:
            self.logger.error(
                f"Forum Thread Creation unexpected error: {type(e).__name__}: {e}"
            )
            raise DiscordAPIError(f"Forum thread creation unexpected error: {e}")

    def create_text_thread(
        self, channel_id: str, name: str, token: str
    ) -> Optional[str]:
        """Create new text channel thread via Discord bot API. Returns thread_id if successful."""
        url = f"https://discord.com/api/v10/channels/{channel_id}/threads"
        data = {"name": name, "type": 11}  # 11 = public thread
        headers = {
            **self.headers_base,
            "Content-Type": "application/json",
            "Authorization": f"Bot {token}",
        }

        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status = response.status
                self.logger.debug(f"Text Thread Creation response: {status}")

                if 200 <= status < 300:
                    # Parse response to get thread_id
                    response_data = json.loads(response.read().decode("utf-8"))
                    return cast(Optional[str], response_data.get("id"))  # thread_id
                return None

        except urllib.error.HTTPError as e:
            self.logger.error(f"Text Thread Creation HTTP error {e.code}: {e.reason}")
            raise DiscordAPIError(f"Text thread creation failed: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            self.logger.error(f"Text Thread Creation URL error: {e.reason}")
            raise DiscordAPIError(f"Text thread creation connection failed: {e.reason}")
        except Exception as e:
            self.logger.error(
                f"Text Thread Creation unexpected error: {type(e).__name__}: {e}"
            )
            raise DiscordAPIError(f"Text thread creation unexpected error: {e}")


# Formatter base class
class EventFormatter(Protocol):
    """Protocol for event formatters."""

    def format(self, event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed."""
        ...


# Thread management
def get_or_create_thread(
    session_id: str, config: Config, http_client: HTTPClient, logger: logging.Logger
) -> Optional[str]:
    """Get existing thread ID or create new thread for session. Returns thread_id if successful."""
    if not config["use_threads"]:
        return None

    # Check cache first
    if session_id in SESSION_THREAD_CACHE:
        logger.debug(
            f"Found existing thread for session {session_id}: {SESSION_THREAD_CACHE[session_id]}"
        )
        return SESSION_THREAD_CACHE[session_id]

    # Create thread name
    thread_name = f"{config['thread_prefix']} {session_id[:8]}"
    logger.debug(f"Creating new thread: {thread_name}")

    try:
        thread_id = None

        if config["channel_type"] == "forum":
            # Forum channels: Use webhook with thread_name
            if config["webhook_url"]:
                # We'll handle thread creation in the actual message sending
                # For now, just return None to indicate we need to create it
                return None
            else:
                logger.warning("Forum channel threads require webhook URL")
                return None

        elif config["channel_type"] == "text":
            # Text channels: Use bot API to create thread
            if config["bot_token"] and config["channel_id"]:
                thread_id = http_client.create_text_thread(
                    config["channel_id"], thread_name, config["bot_token"]
                )
                if thread_id:
                    SESSION_THREAD_CACHE[session_id] = thread_id
                    logger.info(
                        f"Created text thread {thread_id} for session {session_id}"
                    )
                else:
                    logger.warning(
                        f"Failed to create text thread for session {session_id}"
                    )
            else:
                logger.warning("Text channel threads require bot token and channel ID")
                return None

        return thread_id

    except DiscordAPIError as e:
        logger.error(f"Failed to create thread for session {session_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error creating thread for session {session_id}: {e}")
        return None


# Configuration loader
class ConfigLoader:
    """Configuration loader with validation."""

    @staticmethod
    def load() -> Config:
        """Load Discord configuration with clear precedence: env vars override file config."""
        # 1. Start with defaults
        config: Config = {
            "webhook_url": None,
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": "Session",
            "mention_user_id": None,
            "enabled_events": None,
            "disabled_events": None,
        }

        # 2. Load from .env.discord file if it exists
        env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
        if env_file.exists():
            try:
                env_vars = parse_env_file(env_file)

                if ENV_WEBHOOK_URL in env_vars:
                    config["webhook_url"] = env_vars[ENV_WEBHOOK_URL]
                if ENV_BOT_TOKEN in env_vars:
                    config["bot_token"] = env_vars[ENV_BOT_TOKEN]
                if ENV_CHANNEL_ID in env_vars:
                    config["channel_id"] = env_vars[ENV_CHANNEL_ID]
                if ENV_DEBUG in env_vars:
                    config["debug"] = env_vars[ENV_DEBUG] == "1"
                if ENV_USE_THREADS in env_vars:
                    config["use_threads"] = env_vars[ENV_USE_THREADS] == "1"
                if ENV_CHANNEL_TYPE in env_vars:
                    channel_type = env_vars[ENV_CHANNEL_TYPE]
                    if channel_type in ["text", "forum"]:
                        config["channel_type"] = cast(Literal["text", "forum"], channel_type)
                if ENV_THREAD_PREFIX in env_vars:
                    config["thread_prefix"] = env_vars[ENV_THREAD_PREFIX]
                if ENV_MENTION_USER_ID in env_vars:
                    config["mention_user_id"] = env_vars[ENV_MENTION_USER_ID]
                if ENV_ENABLED_EVENTS in env_vars:
                    enabled_events = parse_event_list(env_vars[ENV_ENABLED_EVENTS])
                    config["enabled_events"] = enabled_events if enabled_events else None
                if ENV_DISABLED_EVENTS in env_vars:
                    disabled_events = parse_event_list(env_vars[ENV_DISABLED_EVENTS])
                    config["disabled_events"] = disabled_events if disabled_events else None

            except ConfigurationError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)

        # 3. Environment variables override file config
        if os.environ.get(ENV_WEBHOOK_URL):
            config["webhook_url"] = os.environ.get(ENV_WEBHOOK_URL)
        if os.environ.get(ENV_BOT_TOKEN):
            config["bot_token"] = os.environ.get(ENV_BOT_TOKEN)
        if os.environ.get(ENV_CHANNEL_ID):
            config["channel_id"] = os.environ.get(ENV_CHANNEL_ID)
        if os.environ.get(ENV_DEBUG):
            config["debug"] = os.environ.get(ENV_DEBUG) == "1"
        if os.environ.get(ENV_USE_THREADS):
            config["use_threads"] = os.environ.get(ENV_USE_THREADS) == "1"
        if os.environ.get(ENV_CHANNEL_TYPE):
            env_channel_type: Optional[str] = os.environ.get(ENV_CHANNEL_TYPE)
            if env_channel_type is not None and env_channel_type in ["text", "forum"]:
                config["channel_type"] = cast(Literal["text", "forum"], env_channel_type)
        if os.environ.get(ENV_THREAD_PREFIX):
            thread_prefix = os.environ.get(ENV_THREAD_PREFIX)
            if thread_prefix is not None:
                config["thread_prefix"] = thread_prefix
        if os.environ.get(ENV_MENTION_USER_ID):
            config["mention_user_id"] = os.environ.get(ENV_MENTION_USER_ID)
        if os.environ.get(ENV_ENABLED_EVENTS):
            enabled_events = parse_event_list(os.environ.get(ENV_ENABLED_EVENTS, ""))
            config["enabled_events"] = enabled_events if enabled_events else None
        if os.environ.get(ENV_DISABLED_EVENTS):
            disabled_events = parse_event_list(os.environ.get(ENV_DISABLED_EVENTS, ""))
            config["disabled_events"] = disabled_events if disabled_events else None

        return config

    @staticmethod
    def validate(config: Config) -> None:
        """Validate configuration."""
        if not config["webhook_url"] and not (
            config["bot_token"] and config["channel_id"]
        ):
            raise ConfigurationError(
                "No Discord configuration found. Please set webhook URL or bot token/channel ID."
            )


def setup_logging(debug: bool) -> logging.Logger:
    """Set up logging with optional debug mode."""
    logger = logging.getLogger(__name__)

    if debug:
        log_dir = Path.home() / ".claude" / "hooks" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = (
            log_dir / f"discord_notifier_{datetime.now().strftime('%Y-%m-%d')}.log"
        )

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_file, mode="a"),
                logging.StreamHandler(sys.stderr),
            ],
        )
    else:
        # Only log errors to stderr in non-debug mode
        logging.basicConfig(
            level=logging.ERROR,
            format="%(levelname)s: %(message)s",
            handlers=[logging.StreamHandler(sys.stderr)],
        )

    return logger


# Tool-specific formatters
def format_bash_pre_use(tool_input: dict[str, Any]) -> list[str]:
    """Format Bash tool pre-use details."""
    desc_parts: list[str] = []
    command: str = tool_input.get("command", "")
    desc: str = tool_input.get("description", "")

    # Show full command up to limit
    truncated_command = truncate_string(command, TruncationLimits.COMMAND_FULL)
    add_field(desc_parts, "Command", truncated_command, code=True)

    if desc:
        add_field(desc_parts, "Description", desc)

    return desc_parts


def format_file_operation_pre_use(
    tool_name: str, tool_input: dict[str, Any]
) -> list[str]:
    """Format file operation tool pre-use details."""
    desc_parts: list[str] = []
    file_path: str = tool_input.get("file_path", "")

    if file_path:
        formatted_path = format_file_path(file_path)
        add_field(desc_parts, "File", formatted_path, code=True)

    # Add specific details for each file operation
    if tool_name == ToolNames.EDIT.value:
        old_str: str = tool_input.get("old_string", "")
        new_str: str = tool_input.get("new_string", "")

        if old_str:
            truncated = truncate_string(old_str, TruncationLimits.STRING_PREVIEW)
            suffix = get_truncation_suffix(
                len(old_str), TruncationLimits.STRING_PREVIEW
            )
            add_field(desc_parts, "Replacing", f"{truncated}{suffix}", code=True)

        if new_str:
            truncated = truncate_string(new_str, TruncationLimits.STRING_PREVIEW)
            suffix = get_truncation_suffix(
                len(new_str), TruncationLimits.STRING_PREVIEW
            )
            add_field(desc_parts, "With", f"{truncated}{suffix}", code=True)

    elif tool_name == ToolNames.MULTI_EDIT.value:
        edits = tool_input.get("edits", [])
        add_field(desc_parts, "Number of edits", str(len(edits)))

    elif tool_name == ToolNames.READ.value:
        offset = tool_input.get("offset")
        limit = tool_input.get("limit")
        if offset or limit:
            start_line = offset or 1
            if limit:
                end_line = start_line + limit
                range_str = f"lines {start_line}-{end_line}"
            else:
                range_str = f"lines {start_line}-end"
            add_field(desc_parts, "Range", range_str)

    return desc_parts


def format_search_tool_pre_use(tool_name: str, tool_input: dict[str, Any]) -> list[str]:
    """Format search tool pre-use details."""
    desc_parts: list[str] = []
    pattern: str = tool_input.get("pattern", "")
    add_field(desc_parts, "Pattern", pattern, code=True)

    path: str = tool_input.get("path", "")
    if path:
        add_field(desc_parts, "Path", path, code=True)

    if tool_name == ToolNames.GREP.value:
        include: str = tool_input.get("include", "")
        if include:
            add_field(desc_parts, "Include", include, code=True)

    return desc_parts


def format_task_pre_use(tool_input: dict[str, Any]) -> list[str]:
    """Format Task tool pre-use details."""
    desc_parts: list[str] = []
    desc: str = tool_input.get("description", "")
    prompt: str = tool_input.get("prompt", "")

    if desc:
        add_field(desc_parts, "Task", desc)

    if prompt:
        truncated = truncate_string(prompt, TruncationLimits.PROMPT_PREVIEW)
        suffix = get_truncation_suffix(len(prompt), TruncationLimits.PROMPT_PREVIEW)
        add_field(desc_parts, "Prompt", f"{truncated}{suffix}")

    return desc_parts


def format_web_fetch_pre_use(tool_input: dict[str, Any]) -> list[str]:
    """Format WebFetch tool pre-use details."""
    desc_parts: list[str] = []
    url: str = tool_input.get("url", "")
    prompt: str = tool_input.get("prompt", "")

    if url:
        add_field(desc_parts, "URL", url, code=True)

    if prompt:
        truncated = truncate_string(prompt, TruncationLimits.STRING_PREVIEW)
        suffix = get_truncation_suffix(len(prompt), TruncationLimits.STRING_PREVIEW)
        add_field(desc_parts, "Query", f"{truncated}{suffix}")

    return desc_parts


def format_unknown_tool_pre_use(tool_input: dict[str, Any]) -> list[str]:
    """Format unknown tool pre-use details."""
    return [format_json_field(tool_input, "Input")]


def format_pre_tool_use(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PreToolUse event with detailed information."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"About to execute: {emoji} {tool_name}"}  # type: ignore[typeddict-item]

    # Build detailed description
    desc_parts: list[str] = []
    add_field(desc_parts, "Session", session_id, code=True)

    # Dispatch to tool-specific formatter
    if is_bash_tool(tool_name):
        desc_parts.extend(format_bash_pre_use(tool_input))
    elif is_file_tool(tool_name):
        desc_parts.extend(format_file_operation_pre_use(tool_name, tool_input))
    elif is_search_tool(tool_name):
        desc_parts.extend(format_search_tool_pre_use(tool_name, tool_input))
    elif tool_name == ToolNames.TASK.value:
        desc_parts.extend(format_task_pre_use(tool_input))
    elif tool_name == ToolNames.WEB_FETCH.value:
        desc_parts.extend(format_web_fetch_pre_use(tool_input))
    else:
        desc_parts.extend(format_unknown_tool_pre_use(tool_input))

    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_field(desc_parts, "Time", timestamp)

    embed["description"] = "\n".join(desc_parts)
    return embed


# Post-use formatters
def format_bash_post_use(
    tool_input: dict[str, Any], tool_response: ToolResponse
) -> list[str]:
    """Format Bash tool post-use results."""
    desc_parts: list[str] = []

    command: str = truncate_string(
        tool_input.get("command", ""), TruncationLimits.COMMAND_PREVIEW
    )
    add_field(desc_parts, "Command", command, code=True)

    if isinstance(tool_response, dict):
        stdout = str(tool_response.get("stdout", "")).strip()
        stderr = str(tool_response.get("stderr", "")).strip()
        interrupted = tool_response.get("interrupted", False)

        if stdout:
            truncated_stdout = truncate_string(stdout, TruncationLimits.OUTPUT_PREVIEW)
            desc_parts.append(f"**Output:**\n```\n{truncated_stdout}\n```")

        if stderr:
            truncated_stderr = truncate_string(stderr, TruncationLimits.ERROR_PREVIEW)
            desc_parts.append(f"**Error:**\n```\n{truncated_stderr}\n```")

        if interrupted:
            desc_parts.append("**Status:** ⚠️ Interrupted")

    return desc_parts


def format_read_operation_post_use(
    tool_name: str, tool_input: dict[str, Any], tool_response: ToolResponse
) -> list[str]:
    """Format read operation tool post-use results."""
    desc_parts: list[str] = []

    if tool_name == ToolNames.READ.value:
        file_path = format_file_path(tool_input.get("file_path", ""))
        add_field(desc_parts, "File", file_path, code=True)

        if isinstance(tool_response, str):
            lines = tool_response.count("\n") + 1
            add_field(desc_parts, "Lines read", str(lines))
        elif isinstance(tool_response, dict) and "error" in tool_response:
            # Type assertion: if "error" exists, we can safely access it
            error_value = tool_response.get("error")
            if error_value:
                add_field(desc_parts, "Error", str(error_value))

    elif is_list_tool(tool_name):
        if isinstance(tool_response, list):
            add_field(desc_parts, "Results found", str(len(tool_response)))
            if tool_response:
                preview = tool_response[:5]
                preview_str = "\n".join(f"  • `{item}`" for item in preview)
                desc_parts.append(f"**Preview:**\n{preview_str}")
                if len(tool_response) > 5:
                    desc_parts.append(f"  *... and {len(tool_response) - 5} more*")
        elif isinstance(tool_response, str):
            result_lines: list[str] = tool_response.strip().split("\n") if tool_response.strip() else []
            add_field(desc_parts, "Results found", str(len(result_lines)))

    return desc_parts


def format_write_operation_post_use(
    tool_input: dict[str, Any], tool_response: ToolResponse
) -> list[str]:
    """Format write operation tool post-use results."""
    desc_parts: list[str] = []

    file_path = format_file_path(tool_input.get("file_path", ""))
    add_field(desc_parts, "File", file_path, code=True)

    if isinstance(tool_response, dict):
        if tool_response.get("success"):
            desc_parts.append("**Status:** ✅ Success")
        elif "error" in tool_response:
            # Type assertion: if "error" exists, we can safely access it
            error_value = tool_response.get("error")
            if error_value:
                add_field(desc_parts, "Error", str(error_value))
    elif isinstance(tool_response, str) and "error" in tool_response.lower():
        error_msg = truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)
        add_field(desc_parts, "Error", error_msg)
    else:
        desc_parts.append("**Status:** ✅ Completed")

    return desc_parts


def format_task_post_use(
    tool_input: dict[str, Any], tool_response: ToolResponse
) -> list[str]:
    """Format Task tool post-use results."""
    desc_parts: list[str] = []

    desc: str = tool_input.get("description", "")
    if desc:
        add_field(desc_parts, "Task", desc)

    if isinstance(tool_response, str):
        summary = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        desc_parts.append(f"**Result:**\n{summary}")

    return desc_parts


def format_web_fetch_post_use(
    tool_input: dict[str, Any], tool_response: ToolResponse
) -> list[str]:
    """Format WebFetch tool post-use results."""
    desc_parts: list[str] = []

    url: str = tool_input.get("url", "")
    add_field(desc_parts, "URL", url, code=True)

    if isinstance(tool_response, str):
        if "error" in tool_response.lower():
            error_msg = truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)
            add_field(desc_parts, "Error", error_msg)
        else:
            add_field(desc_parts, "Content length", f"{len(tool_response)} chars")

    return desc_parts


def format_unknown_tool_post_use(tool_response: ToolResponse) -> list[str]:
    """Format unknown tool post-use results."""
    desc_parts: list[str] = []

    if isinstance(tool_response, dict):
        desc_parts.append(
            format_json_field(
                tool_response, "Response", TruncationLimits.RESULT_PREVIEW
            )
        )
    elif isinstance(tool_response, str):
        response_str = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        add_field(desc_parts, "Response", response_str)

    return desc_parts


def format_post_tool_use(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PostToolUse event with execution results."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    tool_response = event_data.get("tool_response", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"Completed: {emoji} {tool_name}"}  # type: ignore[typeddict-item]

    # Build detailed description
    desc_parts: list[str] = []
    add_field(desc_parts, "Session", session_id, code=True)

    # Dispatch to tool-specific formatter
    if is_bash_tool(tool_name):
        desc_parts.extend(format_bash_post_use(tool_input, tool_response))
    elif tool_name == ToolNames.READ.value:
        desc_parts.extend(
            format_read_operation_post_use(tool_name, tool_input, tool_response)
        )
    elif is_list_tool(tool_name):
        desc_parts.extend(
            format_read_operation_post_use(tool_name, tool_input, tool_response)
        )
    elif is_file_tool(tool_name):
        desc_parts.extend(format_write_operation_post_use(tool_input, tool_response))
    elif tool_name == ToolNames.TASK.value:
        desc_parts.extend(format_task_post_use(tool_input, tool_response))
    elif tool_name == ToolNames.WEB_FETCH.value:
        desc_parts.extend(format_web_fetch_post_use(tool_input, tool_response))
    else:
        desc_parts.extend(format_unknown_tool_post_use(tool_response))

    # Add execution time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    add_field(desc_parts, "Completed at", timestamp)

    embed["description"] = "\n".join(desc_parts)
    return embed


def format_notification(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Notification event with full details."""
    message = event_data.get("message", "System notification")

    desc_parts: list[str] = [
        f"**Message:** {message}",
        f"**Session:** `{session_id}`",
        f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Add any additional data from the event
    extra_keys: list[str] = [
        k
        for k in event_data.keys()
        if k not in ["message", "session_id", "transcript_path", "hook_event_name"]
    ]

    if extra_keys:
        for key in extra_keys:
            value = event_data[key]
            if isinstance(value, (str, int, float, bool)):
                add_field(desc_parts, key.title(), str(value))
            else:
                # For complex types, show as JSON
                desc_parts.append(
                    format_json_field(
                        value, key.title(), TruncationLimits.PROMPT_PREVIEW
                    )
                )

    return {"title": "📢 Notification", "description": "\n".join(desc_parts)}  # type: ignore[typeddict-item]


def format_stop(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Stop event with session details."""
    desc_parts: list[str] = []

    add_field(desc_parts, "Session ID", session_id, code=True)
    add_field(desc_parts, "Ended at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Add transcript path if available
    transcript_path = event_data.get("transcript_path", "")
    if transcript_path:
        add_field(desc_parts, "Transcript", transcript_path, code=True)

    # Add any session statistics if available
    for key in ["duration", "tools_used", "messages_exchanged"]:
        if key in event_data:
            label = key.replace("_", " ").title()
            add_field(desc_parts, label, str(event_data[key]))

    return {"title": "🏁 Session Ended", "description": "\n".join(desc_parts)}  # type: ignore[typeddict-item]


def format_subagent_stop(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format SubagentStop event with task results."""
    desc_parts: list[str] = []

    add_field(desc_parts, "Session", session_id, code=True)
    add_field(desc_parts, "Completed at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # Add task description if available
    task_desc = event_data.get("task_description", "")
    if task_desc:
        add_field(desc_parts, "Task", task_desc)

    # Add result summary if available
    result = event_data.get("result", "")
    if result:
        if isinstance(result, str):
            result_summary = truncate_string(result, TruncationLimits.JSON_PREVIEW)
            desc_parts.append(f"**Result:**\n{result_summary}")
        else:
            desc_parts.append(
                format_json_field(result, "Result", TruncationLimits.JSON_PREVIEW)
            )

    # Add execution stats if available
    for key in ["execution_time", "tools_used", "status"]:
        if key in event_data:
            label = key.replace("_", " ").title()
            add_field(desc_parts, label, str(event_data[key]))

    return {"title": "🤖 Subagent Completed", "description": "\n".join(desc_parts)}  # type: ignore[typeddict-item]


def format_default_impl(
    event_type: str, event_data: dict[str, Any], session_id: str
) -> DiscordEmbed:
    """Format unknown event types."""
    desc_parts: list[str] = []
    desc_parts.append(f"**Session:** `{session_id}`")
    desc_parts.append(f"**Event Type:** {event_type}")
    
    # Show event data if available
    if event_data:
        desc_parts.append("\n**Event Data:**")
        desc_parts.append(format_json_field(event_data, "", TruncationLimits.JSON_PREVIEW))
    
    return {"title": f"⚡ {event_type}", "description": "\n".join(desc_parts)}  # type: ignore[typeddict-item]


def format_default(event_data: dict[str, Any], session_id: str) -> DiscordEmbed:
    """Wrapper for format_default_impl that matches the formatter signature."""
    return format_default_impl("Unknown", event_data, session_id)


# Event formatter registry
class FormatterRegistry:
    """Registry for event formatters."""

    def __init__(self) -> None:
        self._formatters: dict[str, Callable[[dict[str, Any], str], DiscordEmbed]] = {
            EventTypes.PRE_TOOL_USE.value: format_pre_tool_use,
            EventTypes.POST_TOOL_USE.value: format_post_tool_use,
            EventTypes.NOTIFICATION.value: format_notification,
            EventTypes.STOP.value: format_stop,
            EventTypes.SUBAGENT_STOP.value: format_subagent_stop,
        }

    def get_formatter(
        self, event_type: str
    ) -> Callable[[dict[str, Any], str], DiscordEmbed]:
        """Get formatter for event type."""
        if event_type in self._formatters:
            return self._formatters[event_type]
        else:
            # Return a lambda that captures the event_type for unknown events
            return lambda event_data, session_id: format_default_impl(
                event_type, event_data, session_id
            )

    def register(
        self, event_type: str, formatter: Callable[[dict[str, Any], str], DiscordEmbed]
    ) -> None:
        """Register a new formatter."""
        self._formatters[event_type] = formatter


def format_event(
    event_type: str,
    event_data: dict[str, Any],
    registry: FormatterRegistry,
    config: Config,
) -> DiscordMessage:
    """Format Claude Code event into Discord embed with length limits."""
    timestamp = datetime.now().isoformat()
    session_id = event_data.get("session_id", "unknown")[:8]

    # Get formatter for event type
    formatter = registry.get_formatter(event_type)
    embed = formatter(event_data, session_id)

    # Enforce Discord's length limits
    if "title" in embed and len(embed["title"]) > DiscordLimits.MAX_TITLE_LENGTH:
        embed["title"] = truncate_string(embed["title"], DiscordLimits.MAX_TITLE_LENGTH)

    if (
        "description" in embed
        and len(embed["description"]) > DiscordLimits.MAX_DESCRIPTION_LENGTH
    ):
        embed["description"] = truncate_string(
            embed["description"], DiscordLimits.MAX_DESCRIPTION_LENGTH
        )

    # Add common fields
    embed["timestamp"] = timestamp

    # Get color for event type
    if is_valid_event_type(event_type):
        embed["color"] = EVENT_COLORS.get(event_type, DiscordColors.DEFAULT)  # type: ignore[call-overload]
    else:
        embed["color"] = DiscordColors.DEFAULT

    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    # Create message with embeds
    message: DiscordMessage = {"embeds": [embed]}  # type: ignore[typeddict-item]

    # Add user mention for Notification and Stop events if configured
    if event_type in [EventTypes.NOTIFICATION.value, EventTypes.STOP.value] and config.get("mention_user_id"):
        # Extract appropriate message based on event type
        if event_type == EventTypes.NOTIFICATION.value:
            display_message = event_data.get("message", "System notification")
        else:  # Stop event
            display_message = "Session ended"
        # Include both mention and message for better Windows notification visibility
        message["content"] = f"<@{config['mention_user_id']}> {display_message}"

    return message


def send_to_discord(
    message: DiscordMessage,
    config: Config,
    logger: logging.Logger,
    http_client: HTTPClient,
    session_id: str = "",
) -> bool:
    """Send message to Discord via webhook or bot API, with optional thread support."""
    # Handle thread support if enabled
    if config["use_threads"] and session_id:
        thread_id = get_or_create_thread(session_id, config, http_client, logger)

        if thread_id:
            # Send to existing thread
            if config["webhook_url"]:
                try:
                    return http_client.post_webhook_to_thread(
                        config["webhook_url"], message, thread_id
                    )
                except DiscordAPIError:
                    logger.warning(
                        "Failed to send to thread, falling back to regular channel"
                    )

        elif config["channel_type"] == "forum" and config["webhook_url"]:
            # Create forum thread with first message
            thread_name = f"{config['thread_prefix']} {session_id[:8]}"
            thread_message: DiscordThreadMessage = {
                "embeds": message.get("embeds", []),
                "thread_name": thread_name,
            }

            try:
                thread_id = http_client.create_forum_thread(
                    config["webhook_url"], thread_message, thread_name
                )
                if thread_id:
                    SESSION_THREAD_CACHE[session_id] = thread_id
                    logger.info(
                        f"Created forum thread {thread_id} for session {session_id}"
                    )
                    return True
                else:
                    logger.warning(
                        "Forum thread creation failed, falling back to regular channel"
                    )
            except DiscordAPIError:
                logger.warning(
                    "Forum thread creation failed, falling back to regular channel"
                )

    # Regular channel messaging (no threads or fallback)
    # Try webhook first
    if config["webhook_url"]:
        try:
            return http_client.post_webhook(config["webhook_url"], message)
        except DiscordAPIError:
            pass  # Fall through to bot API

    # Try bot API as fallback
    if config["bot_token"] and config["channel_id"]:
        try:
            url = (
                f"https://discord.com/api/v10/channels/{config['channel_id']}/messages"
            )
            return http_client.post_bot_api(url, message, config["bot_token"])
        except DiscordAPIError:
            pass

    return False


def main() -> None:
    """Main entry point - read event from stdin and send to Discord."""
    # Load configuration
    config = ConfigLoader.load()
    logger = setup_logging(config["debug"])

    # Check if Discord is configured
    try:
        ConfigLoader.validate(config)
    except ConfigurationError:
        logger.debug("No Discord configuration found")
        sys.exit(0)  # Exit gracefully

    # Initialize components
    http_client = HTTPClient(logger)
    formatter_registry = FormatterRegistry()

    try:
        # Read event data from stdin
        raw_input = sys.stdin.read()
        event_data = json.loads(raw_input)

        # Get event type from environment
        event_type = os.environ.get(ENV_HOOK_EVENT, "Unknown")

        # Check if this event should be processed based on filtering configuration
        if not should_process_event(event_type, config):
            logger.debug(f"Event {event_type} filtered out by configuration")
            sys.exit(0)  # Exit gracefully without processing

        logger.info(f"Processing {event_type} event")
        logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")

        # Format and send message
        message = format_event(event_type, event_data, formatter_registry, config)
        session_id = event_data.get("session_id", "")
        success = send_to_discord(message, config, logger, http_client, session_id)

        if success:
            logger.info(f"{event_type} notification sent successfully")
        else:
            logger.error(f"Failed to send {event_type} notification")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
    except EventProcessingError as e:
        logger.error(f"Event processing error: {e}")
    except Exception as e:
        # Catch any other unexpected errors to ensure we don't block Claude Code
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")

    # Always exit 0 to not block Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
