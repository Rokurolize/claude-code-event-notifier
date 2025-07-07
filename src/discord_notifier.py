#!/usr/bin/env python3
"""
Simplified Claude Code Discord Notifier - All functionality in one file.

Sends Claude Code hook events to Discord using webhook or bot API.
No external dependencies, just Python standard library.
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
    Dict,
    Any,
    Optional,
    Union,
    List,
    TypedDict,
    Literal,
    Callable,
    TypeGuard,
    Protocol,
    Final,
)
from enum import Enum
from dataclasses import dataclass


# Custom exceptions
class DiscordNotifierError(Exception):
    """Base exception for Discord notifier."""

    pass


class ConfigurationError(DiscordNotifierError):
    """Configuration related errors."""

    pass


class DiscordAPIError(DiscordNotifierError):
    """Discord API related errors."""

    pass


class EventProcessingError(DiscordNotifierError):
    """Event processing related errors."""

    pass


class InvalidEventTypeError(EventProcessingError):
    """Invalid event type error."""

    pass


# Type definitions
class Config(TypedDict):
    """Configuration for Discord notifier."""

    webhook_url: Optional[str]
    bot_token: Optional[str]
    channel_id: Optional[str]
    debug: bool


class DiscordFooter(TypedDict):
    """Discord footer structure."""

    text: str


class DiscordEmbed(TypedDict, total=False):
    """Discord embed structure."""

    title: str
    description: str
    color: int
    timestamp: str
    footer: DiscordFooter


class DiscordMessage(TypedDict):
    """Discord message structure."""

    embeds: List[DiscordEmbed]


# Tool input types
class BashToolInput(TypedDict, total=False):
    """Bash tool input structure."""

    command: str
    description: str


class FileToolInput(TypedDict, total=False):
    """File operation tool input structure."""

    file_path: str
    old_string: str
    new_string: str
    edits: List[Dict[str, str]]
    offset: Optional[int]
    limit: Optional[int]


class SearchToolInput(TypedDict, total=False):
    """Search tool input structure."""

    pattern: str
    path: str
    include: str


class TaskToolInput(TypedDict, total=False):
    """Task tool input structure."""

    description: str
    prompt: str


class WebToolInput(TypedDict, total=False):
    """Web tool input structure."""

    url: str
    prompt: str


# Tool response types
class BashToolResponse(TypedDict):
    """Bash tool response structure."""

    stdout: str
    stderr: str
    interrupted: bool
    isImage: bool


class FileOperationResponse(TypedDict):
    """File operation response structure."""

    success: bool
    error: Optional[str]
    filePath: Optional[str]


# Event data types
class BaseEventData(TypedDict):
    """Base event data structure."""

    session_id: str
    transcript_path: str
    hook_event_name: str


class PreToolUseEventData(BaseEventData):
    """PreToolUse event data structure."""

    tool_name: str
    tool_input: Dict[str, Any]


class PostToolUseEventData(PreToolUseEventData):
    """PostToolUse event data structure."""

    tool_response: Union[str, Dict[str, Any], List[Any]]


class NotificationEventData(BaseEventData):
    """Notification event data structure."""

    message: str
    title: Optional[str]


class StopEventData(BaseEventData):
    """Stop event data structure."""

    stop_hook_active: Optional[bool]
    duration: Optional[float]
    tools_used: Optional[int]
    messages_exchanged: Optional[int]


class SubagentStopEventData(StopEventData):
    """SubagentStop event data structure."""

    task_description: Optional[str]
    result: Optional[Union[str, Dict[str, Any]]]
    execution_time: Optional[float]
    status: Optional[str]


# Union types
ToolInput = Union[
    BashToolInput,
    FileToolInput,
    SearchToolInput,
    TaskToolInput,
    WebToolInput,
    Dict[str, Any],
]

ToolResponse = Union[
    str, BashToolResponse, FileOperationResponse, Dict[str, Any], List[Any]
]

EventData = Union[
    PreToolUseEventData,
    PostToolUseEventData,
    NotificationEventData,
    StopEventData,
    SubagentStopEventData,
    Dict[str, Any],
]

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
EVENT_COLORS: Final[Dict[EventType, int]] = {
    "PreToolUse": DiscordColors.BLUE,
    "PostToolUse": DiscordColors.GREEN,
    "Notification": DiscordColors.ORANGE,
    "Stop": DiscordColors.GRAY,
    "SubagentStop": DiscordColors.PURPLE,
}

# Tool emojis mapping
TOOL_EMOJIS: Final[Dict[str, str]] = {
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
ENV_HOOK_EVENT: Final[str] = "CLAUDE_HOOK_EVENT"

# Other constants
USER_AGENT: Final[str] = "ClaudeCodeDiscordNotifier/1.0"
DEFAULT_TIMEOUT: Final[int] = 10
TRUNCATION_SUFFIX: Final[str] = "..."


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
    """Truncate string to maximum length with suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def format_file_path(file_path: str) -> str:
    """Format file path to be relative if possible."""
    if not file_path:
        return ""

    try:
        path = Path(file_path)
        return str(path.relative_to(Path.cwd()))
    except (ValueError, OSError):
        return path.name


def parse_env_file(file_path: Path) -> Dict[str, str]:
    """Parse environment file and return key-value pairs."""
    env_vars: Dict[str, str] = {}

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


def get_truncation_suffix(original_length: int, limit: int) -> str:
    """Get truncation suffix if text was truncated."""
    return f" {TRUNCATION_SUFFIX}" if original_length > limit else ""


def add_field(
    desc_parts: List[str], label: str, value: str, code: bool = False
) -> None:
    """Add a field to description parts."""
    if code:
        desc_parts.append(f"**{label}:** `{value}`")
    else:
        desc_parts.append(f"**{label}:** {value}")


def format_json_field(
    value: Any, label: str, limit: int = TruncationLimits.JSON_PREVIEW
) -> str:
    """Format a JSON value as a field."""
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
        headers: Dict[str, str],
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
                    return success_check(status)
                return status == success_check

        except urllib.error.HTTPError as e:
            self.logger.error(f"{api_name} HTTP error {e.code}: {e.reason}")
            raise DiscordAPIError(f"{api_name} failed: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            self.logger.error(f"{api_name} URL error: {e.reason}")
            raise DiscordAPIError(f"{api_name} connection failed: {e.reason}")
        except Exception as e:
            self.logger.error(f"{api_name} unexpected error: {type(e).__name__}: {e}")
            raise DiscordAPIError(f"{api_name} unexpected error: {e}")


# Formatter base class
class EventFormatter(Protocol):
    """Protocol for event formatters."""

    def format(self, event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
        """Format event data into Discord embed."""
        ...


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
def format_bash_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format Bash tool pre-use details."""
    desc_parts: List[str] = []
    command = tool_input.get("command", "")
    desc = tool_input.get("description", "")

    # Show full command up to limit
    truncated_command = truncate_string(command, TruncationLimits.COMMAND_FULL)
    add_field(desc_parts, "Command", truncated_command, code=True)

    if desc:
        add_field(desc_parts, "Description", desc)

    return desc_parts


def format_file_operation_pre_use(
    tool_name: str, tool_input: Dict[str, Any]
) -> List[str]:
    """Format file operation tool pre-use details."""
    desc_parts: List[str] = []
    file_path = tool_input.get("file_path", "")

    if file_path:
        formatted_path = format_file_path(file_path)
        add_field(desc_parts, "File", formatted_path, code=True)

    # Add specific details for each file operation
    if tool_name == ToolNames.EDIT.value:
        old_str = tool_input.get("old_string", "")
        new_str = tool_input.get("new_string", "")

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
            range_str = f"lines {offset or 1}-{(offset or 1) + (limit or 'end')}"
            add_field(desc_parts, "Range", range_str)

    return desc_parts


def format_search_tool_pre_use(tool_name: str, tool_input: Dict[str, Any]) -> List[str]:
    """Format search tool pre-use details."""
    desc_parts: List[str] = []
    pattern = tool_input.get("pattern", "")
    add_field(desc_parts, "Pattern", pattern, code=True)

    path = tool_input.get("path", "")
    if path:
        add_field(desc_parts, "Path", path, code=True)

    if tool_name == ToolNames.GREP.value:
        include = tool_input.get("include", "")
        if include:
            add_field(desc_parts, "Include", include, code=True)

    return desc_parts


def format_task_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format Task tool pre-use details."""
    desc_parts: List[str] = []
    desc = tool_input.get("description", "")
    prompt = tool_input.get("prompt", "")

    if desc:
        add_field(desc_parts, "Task", desc)

    if prompt:
        truncated = truncate_string(prompt, TruncationLimits.PROMPT_PREVIEW)
        suffix = get_truncation_suffix(len(prompt), TruncationLimits.PROMPT_PREVIEW)
        add_field(desc_parts, "Prompt", f"{truncated}{suffix}")

    return desc_parts


def format_web_fetch_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format WebFetch tool pre-use details."""
    desc_parts: List[str] = []
    url = tool_input.get("url", "")
    prompt = tool_input.get("prompt", "")

    if url:
        add_field(desc_parts, "URL", url, code=True)

    if prompt:
        truncated = truncate_string(prompt, TruncationLimits.STRING_PREVIEW)
        suffix = get_truncation_suffix(len(prompt), TruncationLimits.STRING_PREVIEW)
        add_field(desc_parts, "Query", f"{truncated}{suffix}")

    return desc_parts


def format_unknown_tool_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format unknown tool pre-use details."""
    return [format_json_field(tool_input, "Input")]


def format_pre_tool_use(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PreToolUse event with detailed information."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"About to execute: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts: List[str] = []
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
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format Bash tool post-use results."""
    desc_parts: List[str] = []

    command = truncate_string(
        tool_input.get("command", ""), TruncationLimits.COMMAND_PREVIEW
    )
    add_field(desc_parts, "Command", command, code=True)

    if isinstance(tool_response, dict):
        stdout = tool_response.get("stdout", "").strip()
        stderr = tool_response.get("stderr", "").strip()
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
    tool_name: str, tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format read operation tool post-use results."""
    desc_parts: List[str] = []

    if tool_name == ToolNames.READ.value:
        file_path = format_file_path(tool_input.get("file_path", ""))
        add_field(desc_parts, "File", file_path, code=True)

        if isinstance(tool_response, str):
            lines = tool_response.count("\n") + 1
            add_field(desc_parts, "Lines read", str(lines))
        elif isinstance(tool_response, dict) and tool_response.get("error"):
            add_field(desc_parts, "Error", str(tool_response["error"]))

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
            lines = tool_response.strip().split("\n") if tool_response.strip() else []
            add_field(desc_parts, "Results found", str(len(lines)))

    return desc_parts


def format_write_operation_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format write operation tool post-use results."""
    desc_parts: List[str] = []

    file_path = format_file_path(tool_input.get("file_path", ""))
    add_field(desc_parts, "File", file_path, code=True)

    if isinstance(tool_response, dict):
        if tool_response.get("success"):
            desc_parts.append("**Status:** ✅ Success")
        elif tool_response.get("error"):
            add_field(desc_parts, "Error", str(tool_response["error"]))
    elif isinstance(tool_response, str) and "error" in tool_response.lower():
        error_msg = truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)
        add_field(desc_parts, "Error", error_msg)
    else:
        desc_parts.append("**Status:** ✅ Completed")

    return desc_parts


def format_task_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format Task tool post-use results."""
    desc_parts: List[str] = []

    desc = tool_input.get("description", "")
    if desc:
        add_field(desc_parts, "Task", desc)

    if isinstance(tool_response, str):
        summary = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        desc_parts.append(f"**Result:**\n{summary}")

    return desc_parts


def format_web_fetch_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format WebFetch tool post-use results."""
    desc_parts: List[str] = []

    url = tool_input.get("url", "")
    add_field(desc_parts, "URL", url, code=True)

    if isinstance(tool_response, str):
        if "error" in tool_response.lower():
            error_msg = truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)
            add_field(desc_parts, "Error", error_msg)
        else:
            add_field(desc_parts, "Content length", f"{len(tool_response)} chars")

    return desc_parts


def format_unknown_tool_post_use(tool_response: ToolResponse) -> List[str]:
    """Format unknown tool post-use results."""
    desc_parts: List[str] = []

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


def format_post_tool_use(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PostToolUse event with execution results."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    tool_response = event_data.get("tool_response", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"Completed: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts: List[str] = []
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


def format_notification(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Notification event with full details."""
    message = event_data.get("message", "System notification")

    desc_parts: List[str] = [
        f"**Message:** {message}",
        f"**Session:** `{session_id}`",
        f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Add any additional data from the event
    extra_keys = [
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

    return {"title": "📢 Notification", "description": "\n".join(desc_parts)}


def format_stop(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Stop event with session details."""
    desc_parts: List[str] = []

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

    return {"title": "🏁 Session Ended", "description": "\n".join(desc_parts)}


def format_subagent_stop(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format SubagentStop event with task results."""
    desc_parts: List[str] = []

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

    return {"title": "🤖 Subagent Completed", "description": "\n".join(desc_parts)}


def format_default(
    event_type: str, event_data: Dict[str, Any], session_id: str
) -> DiscordEmbed:
    """Format unknown event types."""
    return {"title": f"⚡ {event_type}", "description": "Unknown event type"}


# Event formatter registry
class FormatterRegistry:
    """Registry for event formatters."""

    def __init__(self):
        self._formatters: Dict[str, Callable[[Dict[str, Any], str], DiscordEmbed]] = {
            EventTypes.PRE_TOOL_USE.value: format_pre_tool_use,
            EventTypes.POST_TOOL_USE.value: format_post_tool_use,
            EventTypes.NOTIFICATION.value: format_notification,
            EventTypes.STOP.value: format_stop,
            EventTypes.SUBAGENT_STOP.value: format_subagent_stop,
        }

    def get_formatter(
        self, event_type: str
    ) -> Callable[[Dict[str, Any], str], DiscordEmbed]:
        """Get formatter for event type."""
        return self._formatters.get(event_type, format_default)

    def register(
        self, event_type: str, formatter: Callable[[Dict[str, Any], str], DiscordEmbed]
    ) -> None:
        """Register a new formatter."""
        self._formatters[event_type] = formatter


def format_event(
    event_type: str, event_data: Dict[str, Any], registry: FormatterRegistry
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
        embed["color"] = EVENT_COLORS.get(event_type, DiscordColors.DEFAULT)
    else:
        embed["color"] = DiscordColors.DEFAULT

    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    return {"embeds": [embed]}


def send_to_discord(
    message: DiscordMessage,
    config: Config,
    logger: logging.Logger,
    http_client: HTTPClient,
) -> bool:
    """Send message to Discord via webhook or bot API."""
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

        logger.info(f"Processing {event_type} event")
        logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")

        # Format and send message
        message = format_event(event_type, event_data, formatter_registry)
        success = send_to_discord(message, config, logger, http_client)

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
