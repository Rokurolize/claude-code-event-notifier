"""Constants and enums for Discord Notifier.

This module contains all constants, enums, and configuration values
used throughout the Discord Notifier system.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Final


# Enums
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


# Limit constants
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
    DEFAULT: int = 100  # For backward compatibility


@dataclass(frozen=True)
class DiscordLimits:
    """Discord API limits."""

    MAX_TITLE_LENGTH: int = 256
    MAX_DESCRIPTION_LENGTH: int = 4096
    MAX_FIELD_VALUE_LENGTH: int = 1024
    MAX_EMBED_COUNT: int = 10
    EMBED_DESCRIPTION_MAX: int = 4096  # Alias for backward compatibility


# Color constants
@dataclass(frozen=True)
class DiscordColors:
    """Discord embed colors."""

    BLUE: int = 0x3498DB
    GREEN: int = 0x2ECC71
    ORANGE: int = 0xF39C12
    GRAY: int = 0x95A5A6
    PURPLE: int = 0x9B59B6
    DEFAULT: int = 0x808080
    SUCCESS: int = 0x2ECC71  # Alias for backward compatibility


# Event colors mapping
EVENT_TYPE_COLORS: Final[dict[str, int]] = {
    "PreToolUse": DiscordColors.BLUE,
    "PostToolUse": DiscordColors.GREEN,
    "Notification": DiscordColors.ORANGE,
    "Stop": DiscordColors.GRAY,
    "SubagentStop": DiscordColors.PURPLE,
}

# Alias for backward compatibility
EVENT_COLORS = EVENT_TYPE_COLORS

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
ENV_BOT_TOKEN: Final[str] = "DISCORD_TOKEN"  # noqa: S105
ENV_CHANNEL_ID: Final[str] = "DISCORD_CHANNEL_ID"
ENV_DEBUG: Final[str] = "DISCORD_DEBUG"
ENV_USE_THREADS: Final[str] = "DISCORD_USE_THREADS"
ENV_CHANNEL_TYPE: Final[str] = "DISCORD_CHANNEL_TYPE"
ENV_THREAD_PREFIX: Final[str] = "DISCORD_THREAD_PREFIX"
ENV_MENTION_USER_ID: Final[str] = "DISCORD_MENTION_USER_ID"
ENV_ENABLED_EVENTS: Final[str] = "DISCORD_ENABLED_EVENTS"
ENV_DISABLED_EVENTS: Final[str] = "DISCORD_DISABLED_EVENTS"
ENV_THREAD_STORAGE_PATH: Final[str] = "DISCORD_THREAD_STORAGE_PATH"
ENV_THREAD_CLEANUP_DAYS: Final[str] = "DISCORD_THREAD_CLEANUP_DAYS"
ENV_HOOK_EVENT: Final[str] = "CLAUDE_HOOK_EVENT"

# Other constants
USER_AGENT: Final[str] = "ClaudeCodeDiscordNotifier/1.0"
DEFAULT_TIMEOUT: Final[int] = 10
TRUNCATION_SUFFIX: Final[str] = "..."
THREAD_CACHE_EXPIRY: int = 3600
CONFIG_FILE_NAME: str = ".env.discord"


# Export all public constants
__all__ = [
    # Enums
    'ToolNames', 'EventTypes',
    # Limit classes
    'TruncationLimits', 'DiscordLimits',
    # Color classes and mappings
    'DiscordColors', 'EVENT_TYPE_COLORS', 'EVENT_COLORS', 'TOOL_EMOJIS',
    # Environment variables
    'ENV_WEBHOOK_URL', 'ENV_BOT_TOKEN', 'ENV_CHANNEL_ID', 'ENV_DEBUG',
    'ENV_USE_THREADS', 'ENV_CHANNEL_TYPE', 'ENV_THREAD_PREFIX',
    'ENV_MENTION_USER_ID', 'ENV_ENABLED_EVENTS', 'ENV_DISABLED_EVENTS',
    'ENV_THREAD_STORAGE_PATH', 'ENV_THREAD_CLEANUP_DAYS', 'ENV_HOOK_EVENT',
    # Other constants
    'USER_AGENT', 'DEFAULT_TIMEOUT', 'TRUNCATION_SUFFIX',
    'THREAD_CACHE_EXPIRY', 'CONFIG_FILE_NAME',
]