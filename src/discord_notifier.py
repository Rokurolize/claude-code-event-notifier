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
from typing import Dict, Any, Optional, Union, List, TypedDict, Literal, Callable
from enum import Enum


# Type definitions
class Config(TypedDict):
    """Configuration for Discord notifier."""

    webhook_url: Optional[str]
    bot_token: Optional[str]
    channel_id: Optional[str]
    debug: bool


class DiscordEmbed(TypedDict, total=False):
    """Discord embed structure."""

    title: str
    description: str
    color: int
    timestamp: str
    footer: Dict[str, str]


class DiscordMessage(TypedDict):
    """Discord message structure."""

    embeds: List[DiscordEmbed]


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


ToolInput = Union[
    BashToolInput,
    FileToolInput,
    SearchToolInput,
    TaskToolInput,
    WebToolInput,
    Dict[str, Any],
]
ToolResponse = Union[str, Dict[str, Any], List[Any]]

EventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]


def is_valid_event_type(event_type: str) -> bool:
    """Check if event_type is a valid EventType."""
    return event_type in (
        "PreToolUse",
        "PostToolUse",
        "Notification",
        "Stop",
        "SubagentStop",
    )


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


# Constants
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


# Length limits
class TruncationLimits:
    """Character limits for truncation."""

    COMMAND_PREVIEW = 100
    COMMAND_FULL = 500
    STRING_PREVIEW = 100
    PROMPT_PREVIEW = 200
    OUTPUT_PREVIEW = 500
    ERROR_PREVIEW = 300
    RESULT_PREVIEW = 300
    JSON_PREVIEW = 400


# Discord API limits
MAX_TITLE_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 4096
MAX_FIELD_VALUE_LENGTH = 1024

# Event colors for Discord embeds
EVENT_COLORS: Dict[EventType, int] = {
    "PreToolUse": 0x3498DB,  # Blue
    "PostToolUse": 0x2ECC71,  # Green
    "Notification": 0xF39C12,  # Orange
    "Stop": 0x95A5A6,  # Gray
    "SubagentStop": 0x9B59B6,  # Purple
}

# Tool emojis for visual distinction
TOOL_EMOJIS: Dict[str, str] = {
    ToolNames.BASH: "🔧",
    ToolNames.READ: "📖",
    ToolNames.WRITE: "✏️",
    ToolNames.EDIT: "✂️",
    ToolNames.MULTI_EDIT: "📝",
    ToolNames.GLOB: "🔍",
    ToolNames.GREP: "🔎",
    ToolNames.LS: "📁",
    ToolNames.TASK: "🤖",
    ToolNames.WEB_FETCH: "🌐",
    "mcp__human-in-the-loop__ask_human": "💬",
}


# Utility functions
def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
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
        # Fallback: try to get just the filename, or return original if Path creation failed
        try:
            return Path(file_path).name
        except (ValueError, OSError):
            return file_path


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
        raise RuntimeError(f"Error reading {file_path}: {e}")

    return env_vars


def load_config() -> Config:
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

            if "DISCORD_WEBHOOK_URL" in env_vars:
                config["webhook_url"] = env_vars["DISCORD_WEBHOOK_URL"]
            if "DISCORD_TOKEN" in env_vars:
                config["bot_token"] = env_vars["DISCORD_TOKEN"]
            if "DISCORD_CHANNEL_ID" in env_vars:
                config["channel_id"] = env_vars["DISCORD_CHANNEL_ID"]
            if "DISCORD_DEBUG" in env_vars:
                config["debug"] = env_vars["DISCORD_DEBUG"] == "1"

        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)

    # 3. Environment variables override file config
    if os.environ.get("DISCORD_WEBHOOK_URL"):
        config["webhook_url"] = os.environ.get("DISCORD_WEBHOOK_URL")
    if os.environ.get("DISCORD_TOKEN"):
        config["bot_token"] = os.environ.get("DISCORD_TOKEN")
    if os.environ.get("DISCORD_CHANNEL_ID"):
        config["channel_id"] = os.environ.get("DISCORD_CHANNEL_ID")
    if os.environ.get("DISCORD_DEBUG"):
        config["debug"] = os.environ.get("DISCORD_DEBUG") == "1"

    return config


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
    desc_parts = []
    command = tool_input.get("command", "")
    desc = tool_input.get("description", "")

    # Show full command up to limit
    truncated_command = truncate_string(command, TruncationLimits.COMMAND_FULL)
    desc_parts.append(f"**Command:** `{truncated_command}`")

    if desc:
        desc_parts.append(f"**Description:** {desc}")

    return desc_parts


def format_file_operation_pre_use(
    tool_name: str, tool_input: Dict[str, Any]
) -> List[str]:
    """Format file operation tool pre-use details."""
    desc_parts = []
    file_path = tool_input.get("file_path", "")

    if file_path:
        formatted_path = format_file_path(file_path)
        desc_parts.append(f"**File:** `{formatted_path}`")

    # Add specific details for each file operation
    if tool_name == ToolNames.EDIT:
        old_str = truncate_string(
            tool_input.get("old_string", ""), TruncationLimits.STRING_PREVIEW
        )
        new_str = truncate_string(
            tool_input.get("new_string", ""), TruncationLimits.STRING_PREVIEW
        )

        if old_str:
            suffix = (
                " ..."
                if len(tool_input.get("old_string", ""))
                > TruncationLimits.STRING_PREVIEW
                else ""
            )
            desc_parts.append(f"**Replacing:** `{old_str}`{suffix}")
        if new_str:
            suffix = (
                " ..."
                if len(tool_input.get("new_string", ""))
                > TruncationLimits.STRING_PREVIEW
                else ""
            )
            desc_parts.append(f"**With:** `{new_str}`{suffix}")

    elif tool_name == ToolNames.MULTI_EDIT:
        edits = tool_input.get("edits", [])
        desc_parts.append(f"**Number of edits:** {len(edits)}")

    elif tool_name == ToolNames.READ:
        offset = tool_input.get("offset")
        limit = tool_input.get("limit")
        if offset or limit:
            start_line = offset or 1
            if limit:
                end_line = start_line + limit - 1
                desc_parts.append(f"**Range:** lines {start_line}-{end_line}")
            else:
                desc_parts.append(f"**Range:** lines {start_line}-end")

    return desc_parts


def format_search_tool_pre_use(tool_name: str, tool_input: Dict[str, Any]) -> List[str]:
    """Format search tool pre-use details."""
    desc_parts = []
    pattern = tool_input.get("pattern", "")
    desc_parts.append(f"**Pattern:** `{pattern}`")

    path = tool_input.get("path", "")
    if path:
        desc_parts.append(f"**Path:** `{path}`")

    if tool_name == ToolNames.GREP:
        include = tool_input.get("include", "")
        if include:
            desc_parts.append(f"**Include:** `{include}`")

    return desc_parts


def format_task_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format Task tool pre-use details."""
    desc_parts = []
    desc = tool_input.get("description", "")
    prompt = truncate_string(
        tool_input.get("prompt", ""), TruncationLimits.PROMPT_PREVIEW
    )

    if desc:
        desc_parts.append(f"**Task:** {desc}")
    if prompt:
        suffix = (
            " ..."
            if len(tool_input.get("prompt", "")) > TruncationLimits.PROMPT_PREVIEW
            else ""
        )
        desc_parts.append(f"**Prompt:** {prompt}{suffix}")

    return desc_parts


def format_web_fetch_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format WebFetch tool pre-use details."""
    desc_parts = []
    url = tool_input.get("url", "")
    prompt = truncate_string(
        tool_input.get("prompt", ""), TruncationLimits.STRING_PREVIEW
    )

    if url:
        desc_parts.append(f"**URL:** `{url}`")
    if prompt:
        suffix = (
            " ..."
            if len(tool_input.get("prompt", "")) > TruncationLimits.STRING_PREVIEW
            else ""
        )
        desc_parts.append(f"**Query:** {prompt}{suffix}")

    return desc_parts


def format_unknown_tool_pre_use(tool_input: Dict[str, Any]) -> List[str]:
    """Format unknown tool pre-use details."""
    input_str = truncate_string(
        json.dumps(tool_input, indent=2), TruncationLimits.JSON_PREVIEW
    )
    suffix = (
        " ..." if len(json.dumps(tool_input)) > TruncationLimits.JSON_PREVIEW else ""
    )
    return [f"**Input:**\n```json\n{input_str}{suffix}\n```"]


def format_pre_tool_use(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PreToolUse event with detailed information."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"About to execute: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts = []
    desc_parts.append(f"**Session:** `{session_id}`")

    # Dispatch to tool-specific formatter
    if tool_name == ToolNames.BASH:
        desc_parts.extend(format_bash_pre_use(tool_input))
    elif tool_name in [
        ToolNames.WRITE,
        ToolNames.EDIT,
        ToolNames.MULTI_EDIT,
        ToolNames.READ,
    ]:
        desc_parts.extend(format_file_operation_pre_use(tool_name, tool_input))
    elif tool_name in [ToolNames.GLOB, ToolNames.GREP]:
        desc_parts.extend(format_search_tool_pre_use(tool_name, tool_input))
    elif tool_name == ToolNames.TASK:
        desc_parts.extend(format_task_pre_use(tool_input))
    elif tool_name == ToolNames.WEB_FETCH:
        desc_parts.extend(format_web_fetch_pre_use(tool_input))
    else:
        desc_parts.extend(format_unknown_tool_pre_use(tool_input))

    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    desc_parts.append(f"**Time:** {timestamp}")

    embed["description"] = "\n".join(desc_parts)
    return embed


# Post-use formatters
def format_bash_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format Bash tool post-use results."""
    desc_parts = []

    command = truncate_string(
        tool_input.get("command", ""), TruncationLimits.COMMAND_PREVIEW
    )
    desc_parts.append(f"**Command:** `{command}`")

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
    desc_parts = []

    if tool_name == ToolNames.READ:
        file_path = format_file_path(tool_input.get("file_path", ""))
        desc_parts.append(f"**File:** `{file_path}`")

        if isinstance(tool_response, str):
            lines = tool_response.count("\n") + 1
            desc_parts.append(f"**Lines read:** {lines}")
        elif isinstance(tool_response, dict) and tool_response.get("error"):
            desc_parts.append(f"**Error:** {tool_response['error']}")

    elif tool_name in [ToolNames.GLOB, ToolNames.GREP, ToolNames.LS]:
        if isinstance(tool_response, list):
            desc_parts.append(f"**Results found:** {len(tool_response)}")
            if tool_response:
                preview = tool_response[:5]
                preview_str = "\n".join(f"  • `{item}`" for item in preview)
                desc_parts.append(f"**Preview:**\n{preview_str}")
                if len(tool_response) > 5:
                    desc_parts.append(f"  *... and {len(tool_response) - 5} more*")
        elif isinstance(tool_response, str):
            lines = tool_response.strip().split("\n") if tool_response.strip() else []
            desc_parts.append(f"**Results found:** {len(lines)}")

    return desc_parts


def format_write_operation_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format write operation tool post-use results."""
    desc_parts = []

    file_path = format_file_path(tool_input.get("file_path", ""))
    desc_parts.append(f"**File:** `{file_path}`")

    if isinstance(tool_response, dict):
        if tool_response.get("success"):
            desc_parts.append("**Status:** ✅ Success")
        elif tool_response.get("error"):
            desc_parts.append(f"**Error:** {tool_response['error']}")
    elif isinstance(tool_response, str) and "error" in tool_response.lower():
        desc_parts.append(
            f"**Error:** {truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)}"
        )
    else:
        desc_parts.append("**Status:** ✅ Completed")

    return desc_parts


def format_task_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format Task tool post-use results."""
    desc_parts = []

    desc = tool_input.get("description", "")
    if desc:
        desc_parts.append(f"**Task:** {desc}")

    if isinstance(tool_response, str):
        summary = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        desc_parts.append(f"**Result:**\n{summary}")

    return desc_parts


def format_web_fetch_post_use(
    tool_input: Dict[str, Any], tool_response: ToolResponse
) -> List[str]:
    """Format WebFetch tool post-use results."""
    desc_parts = []

    url = tool_input.get("url", "")
    desc_parts.append(f"**URL:** `{url}`")

    if isinstance(tool_response, str):
        if "error" in tool_response.lower():
            desc_parts.append(
                f"**Error:** {truncate_string(tool_response, TruncationLimits.PROMPT_PREVIEW)}"
            )
        else:
            desc_parts.append(f"**Content length:** {len(tool_response)} chars")

    return desc_parts


def format_unknown_tool_post_use(tool_response: ToolResponse) -> List[str]:
    """Format unknown tool post-use results."""
    desc_parts = []

    if isinstance(tool_response, dict):
        response_str = truncate_string(
            json.dumps(tool_response, indent=2), TruncationLimits.RESULT_PREVIEW
        )
        suffix = (
            " ..."
            if len(json.dumps(tool_response)) > TruncationLimits.RESULT_PREVIEW
            else ""
        )
        desc_parts.append(f"**Response:**\n```json\n{response_str}{suffix}\n```")
    elif isinstance(tool_response, str):
        response_str = truncate_string(tool_response, TruncationLimits.RESULT_PREVIEW)
        desc_parts.append(f"**Response:** {response_str}")

    return desc_parts


def format_post_tool_use(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format PostToolUse event with execution results."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    tool_response = event_data.get("tool_response", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed: DiscordEmbed = {"title": f"Completed: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts = []
    desc_parts.append(f"**Session:** `{session_id}`")

    # Dispatch to tool-specific formatter
    if tool_name == ToolNames.BASH:
        desc_parts.extend(format_bash_post_use(tool_input, tool_response))
    elif tool_name in [ToolNames.READ, ToolNames.GLOB, ToolNames.GREP, ToolNames.LS]:
        desc_parts.extend(
            format_read_operation_post_use(tool_name, tool_input, tool_response)
        )
    elif tool_name in [ToolNames.WRITE, ToolNames.EDIT, ToolNames.MULTI_EDIT]:
        desc_parts.extend(format_write_operation_post_use(tool_input, tool_response))
    elif tool_name == ToolNames.TASK:
        desc_parts.extend(format_task_post_use(tool_input, tool_response))
    elif tool_name == ToolNames.WEB_FETCH:
        desc_parts.extend(format_web_fetch_post_use(tool_input, tool_response))
    else:
        desc_parts.extend(format_unknown_tool_post_use(tool_response))

    # Add execution time
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    desc_parts.append(f"**Completed at:** {timestamp}")

    embed["description"] = "\n".join(desc_parts)
    return embed


def format_notification(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Notification event with full details."""
    message = event_data.get("message", "System notification")

    desc_parts = [
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
                desc_parts.append(f"**{key.title()}:** {value}")
            else:
                # For complex types, show as JSON
                value_str = truncate_string(
                    json.dumps(value, indent=2), TruncationLimits.PROMPT_PREVIEW
                )
                suffix = (
                    " ..."
                    if len(json.dumps(value)) > TruncationLimits.PROMPT_PREVIEW
                    else ""
                )
                desc_parts.append(
                    f"**{key.title()}:**\n```json\n{value_str}{suffix}\n```"
                )

    return {"title": "📢 Notification", "description": "\n".join(desc_parts)}


def format_stop(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format Stop event with session details."""
    desc_parts = [
        f"**Session ID:** `{session_id}`",
        f"**Ended at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Add transcript path if available
    transcript_path = event_data.get("transcript_path", "")
    if transcript_path:
        desc_parts.append(f"**Transcript:** `{transcript_path}`")

    # Add any session statistics if available
    for key in ["duration", "tools_used", "messages_exchanged"]:
        if key in event_data:
            desc_parts.append(f"**{key.replace('_', ' ').title()}:** {event_data[key]}")

    return {"title": "🏁 Session Ended", "description": "\n".join(desc_parts)}


def format_subagent_stop(event_data: Dict[str, Any], session_id: str) -> DiscordEmbed:
    """Format SubagentStop event with task results."""
    desc_parts = [
        f"**Session:** `{session_id}`",
        f"**Completed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    # Add task description if available
    task_desc = event_data.get("task_description", "")
    if task_desc:
        desc_parts.append(f"**Task:** {task_desc}")

    # Add result summary if available
    result = event_data.get("result", "")
    if result:
        if isinstance(result, str):
            result_summary = truncate_string(result, TruncationLimits.JSON_PREVIEW)
            desc_parts.append(f"**Result:**\n{result_summary}")
        else:
            result_str = truncate_string(
                json.dumps(result, indent=2), TruncationLimits.JSON_PREVIEW
            )
            suffix = (
                " ..."
                if len(json.dumps(result)) > TruncationLimits.JSON_PREVIEW
                else ""
            )
            desc_parts.append(f"**Result:**\n```json\n{result_str}{suffix}\n```")

    # Add execution stats if available
    for key in ["execution_time", "tools_used", "status"]:
        if key in event_data:
            desc_parts.append(f"**{key.replace('_', ' ').title()}:** {event_data[key]}")

    return {"title": "🤖 Subagent Completed", "description": "\n".join(desc_parts)}


def format_default(
    event_type: str, event_data: Dict[str, Any], session_id: str
) -> DiscordEmbed:
    """Format unknown event types."""
    return {"title": f"⚡ {event_type}", "description": "Unknown event type"}


# Event formatter dispatch table
EVENT_FORMATTERS: Dict[EventType, Callable[[Dict[str, Any], str], DiscordEmbed]] = {
    "PreToolUse": format_pre_tool_use,
    "PostToolUse": format_post_tool_use,
    "Notification": format_notification,
    "Stop": format_stop,
    "SubagentStop": format_subagent_stop,
}


def format_event(event_type: str, event_data: Dict[str, Any]) -> DiscordMessage:
    """Format Claude Code event into Discord embed with length limits."""
    timestamp = datetime.now().isoformat()
    session_id = event_data.get("session_id", "unknown")[:8]

    # Get formatter for event type
    if is_valid_event_type(event_type):
        formatter = EVENT_FORMATTERS.get(event_type)
        if formatter:
            embed = formatter(event_data, session_id)
        else:
            embed = format_default(event_type, event_data, session_id)
    else:
        embed = format_default(event_type, event_data, session_id)

    # Enforce Discord's length limits
    if "title" in embed and len(embed["title"]) > MAX_TITLE_LENGTH:
        embed["title"] = truncate_string(embed["title"], MAX_TITLE_LENGTH)

    if "description" in embed and len(embed["description"]) > MAX_DESCRIPTION_LENGTH:
        embed["description"] = truncate_string(
            embed["description"], MAX_DESCRIPTION_LENGTH
        )

    # Add common fields
    embed["timestamp"] = timestamp
    if is_valid_event_type(event_type):
        embed["color"] = EVENT_COLORS.get(event_type, 0x808080)
    else:
        embed["color"] = 0x808080  # Default color for unknown events
    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    return {"embeds": [embed]}


def send_to_discord(
    message: DiscordMessage, config: Config, logger: logging.Logger
) -> bool:
    """Send message to Discord via webhook or bot API."""
    # Try webhook first
    if config["webhook_url"]:
        try:
            data = json.dumps(message).encode("utf-8")
            req = urllib.request.Request(
                config["webhook_url"],
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ClaudeCodeDiscordNotifier/1.0",
                },
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.debug(f"Webhook response: {response.status}")
                return response.status == 204

        except urllib.error.HTTPError as e:
            logger.error(f"Webhook HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"Webhook URL error: {e.reason}")
        except Exception as e:
            logger.error(f"Webhook unexpected error: {type(e).__name__}: {e}")

    # Try bot API as fallback
    if config["bot_token"] and config["channel_id"]:
        try:
            url = (
                f"https://discord.com/api/v10/channels/{config['channel_id']}/messages"
            )
            data = json.dumps(message).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization": f"Bot {config['bot_token']}",
                    "Content-Type": "application/json",
                    "User-Agent": "ClaudeCodeDiscordNotifier/1.0",
                },
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.debug(f"Bot API response: {response.status}")
                return 200 <= response.status < 300

        except urllib.error.HTTPError as e:
            logger.error(f"Bot API HTTP error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            logger.error(f"Bot API URL error: {e.reason}")
        except Exception as e:
            logger.error(f"Bot API unexpected error: {type(e).__name__}: {e}")

    return False


def main() -> None:
    """Main entry point - read event from stdin and send to Discord."""
    # Load configuration
    config = load_config()
    logger = setup_logging(config["debug"])

    # Check if Discord is configured
    if not config["webhook_url"] and not (config["bot_token"] and config["channel_id"]):
        logger.debug("No Discord configuration found")
        sys.exit(0)  # Exit gracefully

    try:
        # Read event data from stdin
        raw_input = sys.stdin.read()
        event_data = json.loads(raw_input)

        # Get event type from environment
        event_type = os.environ.get("CLAUDE_HOOK_EVENT", "Unknown")

        logger.info(f"Processing {event_type} event")
        logger.debug(f"Event data: {json.dumps(event_data, indent=2)}")

        # Format and send message
        message = format_event(event_type, event_data)
        success = send_to_discord(message, config, logger)

        if success:
            logger.info(f"{event_type} notification sent successfully")
        else:
            logger.error(f"Failed to send {event_type} notification")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
    except KeyError as e:
        logger.error(f"Missing required field: {e}")
    except TypeError as e:
        logger.error(f"Type error in event data: {e}")
    except Exception as e:
        # Catch any other unexpected errors to ensure we don't block Claude Code
        logger.error(f"Unexpected error: {type(e).__name__}: {e}")

    # Always exit 0 to not block Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
