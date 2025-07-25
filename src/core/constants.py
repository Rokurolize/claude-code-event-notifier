#!/usr/bin/env python3
"""Constants and configuration values for Discord Notifier.

This module centralizes all constants, including Discord API limits,
color codes, event mappings, and environment variable names.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal

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
    """Enhanced character limits for truncation with conversation tracking support.
    
    IMPORTANT: These limits have been dramatically increased to reduce information loss.
    Previous limits caused 87.8% information loss for Bash output and 92.7% for errors.
    """

    COMMAND_PREVIEW: int = 200
    COMMAND_FULL: int = 1000
    STRING_PREVIEW: int = 200
    PROMPT_PREVIEW: int = 2500      # Was 500 → Now 2500 (enough for most prompts)
    
    # CRITICAL: Increased to reduce massive information loss
    OUTPUT_PREVIEW: int = 3000      # Was 500 (87.8% loss) → Now 3000 (26.8% loss)
    ERROR_PREVIEW: int = 2500       # Was 300 (92.7% loss) → Now 2500 (39.0% loss)
    RESULT_PREVIEW: int = 2500      # Was 300 (92.7% loss) → Now 2500 (39.0% loss)
    JSON_PREVIEW: int = 2000        # Was 400 (90.2% loss) → Now 2000 (51.2% loss)

    # Discord field limits (use almost full Discord API limits)
    TITLE: int = 256
    DESCRIPTION: int = 3800         # Was 2048 → Now 3800 (95% of Discord's 4096 limit)
    FIELD_NAME: int = 256
    FIELD_VALUE: int = 1024
    FOOTER_TEXT: int = 2048

    # 新規追加 - 会話追跡機能用
    CONVERSATION_LOG: int = 3000    # 会話ログ専用 (increased)
    RESPONSE_CONTENT: int = 3000    # 回答内容専用 (increased)
    MARKDOWN_EXPORT: int = 10000    # Markdownエクスポート専用


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
ENV_BOT_TOKEN: Final[str] = "DISCORD_BOT_TOKEN"  # noqa: S105
ENV_CHANNEL_ID: Final[str] = "DISCORD_CHANNEL_ID"
ENV_DEBUG: Final[str] = "DISCORD_DEBUG"
ENV_USE_THREADS: Final[str] = "DISCORD_USE_THREADS"
ENV_CHANNEL_TYPE: Final[str] = "DISCORD_CHANNEL_TYPE"
ENV_THREAD_PREFIX: Final[str] = "DISCORD_THREAD_PREFIX"
ENV_MENTION_USER_ID: Final[str] = "DISCORD_MENTION_USER_ID"

# Legacy filtering (backward compatibility - prefer individual controls below)
ENV_ENABLED_EVENTS: Final[str] = "DISCORD_ENABLED_EVENTS"
ENV_DISABLED_EVENTS: Final[str] = "DISCORD_DISABLED_EVENTS"
ENV_DISABLED_TOOLS: Final[str] = "DISCORD_DISABLED_TOOLS"

# Individual event controls (recommended - direct and intuitive)
ENV_EVENT_PRETOOLUSE: Final[str] = "DISCORD_EVENT_PRETOOLUSE"
ENV_EVENT_POSTTOOLUSE: Final[str] = "DISCORD_EVENT_POSTTOOLUSE"
ENV_EVENT_NOTIFICATION: Final[str] = "DISCORD_EVENT_NOTIFICATION"
ENV_EVENT_STOP: Final[str] = "DISCORD_EVENT_STOP"
ENV_EVENT_SUBAGENT_STOP: Final[str] = "DISCORD_EVENT_SUBAGENT_STOP"

# Individual tool controls (recommended - direct and intuitive)
ENV_TOOL_READ: Final[str] = "DISCORD_TOOL_READ"
ENV_TOOL_EDIT: Final[str] = "DISCORD_TOOL_EDIT"
ENV_TOOL_MULTIEDIT: Final[str] = "DISCORD_TOOL_MULTIEDIT"
ENV_TOOL_TODOWRITE: Final[str] = "DISCORD_TOOL_TODOWRITE"
ENV_TOOL_GREP: Final[str] = "DISCORD_TOOL_GREP"
ENV_TOOL_GLOB: Final[str] = "DISCORD_TOOL_GLOB"
ENV_TOOL_LS: Final[str] = "DISCORD_TOOL_LS"
ENV_TOOL_BASH: Final[str] = "DISCORD_TOOL_BASH"
ENV_TOOL_TASK: Final[str] = "DISCORD_TOOL_TASK"
ENV_TOOL_WEBFETCH: Final[str] = "DISCORD_TOOL_WEBFETCH"

ENV_THREAD_STORAGE_PATH: Final[str] = "DISCORD_THREAD_STORAGE_PATH"
ENV_THREAD_CLEANUP_DAYS: Final[str] = "DISCORD_THREAD_CLEANUP_DAYS"
ENV_HOOK_EVENT: Final[str] = "CLAUDE_HOOK_EVENT"

# Discord API URLs
DISCORD_API_BASE: Final[str] = "https://discord.com/api/v10"
DISCORD_CDN_BASE: Final[str] = "https://cdn.discordapp.com"

# Other constants
USER_AGENT: Final[str] = "ClaudeCodeDiscordNotifier/1.0"
DEFAULT_TIMEOUT: Final[int] = 10
TRUNCATION_SUFFIX: Final[str] = "..."

# HTTP constants
MAX_RETRIES: Final[int] = 3
RETRY_DELAY: Final[float] = 1.0
RATE_LIMIT_RETRY_DELAY: Final[float] = 5.0

# Thread management defaults
DEFAULT_THREAD_PREFIX: Final[str] = "Claude Code Session"
DEFAULT_THREAD_CLEANUP_DAYS: Final[int] = 30
DEFAULT_THREAD_CACHE_SIZE: Final[int] = 1000

# Logging configuration
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_LEVEL: Final[str] = "INFO"

# Default configuration paths
DEFAULT_STORAGE_PATH: Final[str] = "~/.claude/hooks/discord_threads.db"
