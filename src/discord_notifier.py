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
from typing import Dict, Any, Optional

# Event colors for Discord embeds
EVENT_COLORS = {
    "PreToolUse": 0x3498DB,  # Blue
    "PostToolUse": 0x2ECC71,  # Green
    "Notification": 0xF39C12,  # Orange
    "Stop": 0x95A5A6,  # Gray
    "SubagentStop": 0x9B59B6,  # Purple
}

# Maximum field lengths to prevent Discord API errors
MAX_TITLE_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 4096
MAX_FIELD_VALUE_LENGTH = 1024

# Tool emojis for visual distinction
TOOL_EMOJIS = {
    "Bash": "🔧",
    "Read": "📖",
    "Write": "✏️",
    "Edit": "✂️",
    "MultiEdit": "📝",
    "Glob": "🔍",
    "Grep": "🔎",
    "LS": "📁",
    "Task": "🤖",
    "WebFetch": "🌐",
    "mcp__human-in-the-loop__ask_human": "💬",
}


def load_config() -> Dict[str, str]:
    """Load Discord configuration with clear precedence: env vars override file config."""
    # 1. Start with defaults
    config = {
        "webhook_url": None,
        "bot_token": None,
        "channel_id": None,
        "debug": False,
    }

    # 2. Load from .env.discord file if it exists
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    if env_file.exists():
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        value = value.strip('"').strip("'")

                        if key == "DISCORD_WEBHOOK_URL":
                            config["webhook_url"] = value
                        elif key == "DISCORD_TOKEN":
                            config["bot_token"] = value
                        elif key == "DISCORD_CHANNEL_ID":
                            config["channel_id"] = value
                        elif key == "DISCORD_DEBUG":
                            config["debug"] = value == "1"
        except (IOError, ValueError) as e:
            print(f"Error reading {env_file}: {e}", file=sys.stderr)
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


def format_pre_tool_use(event_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Format PreToolUse event with detailed information."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed = {"title": f"About to execute: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts = []

    # Add session info
    desc_parts.append(f"**Session:** `{session_id}`")

    # Add tool-specific details
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        desc = tool_input.get("description", "")
        # Show full command up to 500 chars
        if len(command) > 500:
            command = command[:497] + "..."
        desc_parts.append(f"**Command:** `{command}`")
        if desc:
            desc_parts.append(f"**Description:** {desc}")
    elif tool_name in ["Write", "Edit", "MultiEdit", "Read"]:
        file_path = tool_input.get("file_path", "")
        if file_path:
            # Show relative path if possible
            try:
                file_path = Path(file_path).relative_to(Path.cwd())
            except:
                file_path = Path(file_path).name
            desc_parts.append(f"**File:** `{file_path}`")

        # Add specific details for each file operation
        if tool_name == "Edit":
            old_str = tool_input.get("old_string", "")[:100]
            new_str = tool_input.get("new_string", "")[:100]
            if old_str:
                desc_parts.append(
                    f"**Replacing:** `{old_str}`{' ...' if len(tool_input.get('old_string', '')) > 100 else ''}"
                )
            if new_str:
                desc_parts.append(
                    f"**With:** `{new_str}`{' ...' if len(tool_input.get('new_string', '')) > 100 else ''}"
                )
        elif tool_name == "MultiEdit":
            edits = tool_input.get("edits", [])
            desc_parts.append(f"**Number of edits:** {len(edits)}")
        elif tool_name == "Read":
            offset = tool_input.get("offset")
            limit = tool_input.get("limit")
            if offset or limit:
                desc_parts.append(
                    f"**Range:** lines {offset or 1}-{(offset or 1) + (limit or 'end')}"
                )

    elif tool_name in ["Glob", "Grep"]:
        pattern = tool_input.get("pattern", "")
        desc_parts.append(f"**Pattern:** `{pattern}`")
        path = tool_input.get("path", "")
        if path:
            desc_parts.append(f"**Path:** `{path}`")
        if tool_name == "Grep":
            include = tool_input.get("include", "")
            if include:
                desc_parts.append(f"**Include:** `{include}`")
    elif tool_name == "Task":
        desc = tool_input.get("description", "")
        prompt = tool_input.get("prompt", "")[:200]
        if desc:
            desc_parts.append(f"**Task:** {desc}")
        if prompt:
            desc_parts.append(
                f"**Prompt:** {prompt}{' ...' if len(tool_input.get('prompt', '')) > 200 else ''}"
            )
    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")
        prompt = tool_input.get("prompt", "")[:100]
        if url:
            desc_parts.append(f"**URL:** `{url}`")
        if prompt:
            desc_parts.append(
                f"**Query:** {prompt}{' ...' if len(tool_input.get('prompt', '')) > 100 else ''}"
            )
    else:
        # For unknown tools, show raw input (truncated)
        input_str = json.dumps(tool_input, indent=2)[:400]
        desc_parts.append(
            f"**Input:**\n```json\n{input_str}{' ...' if len(json.dumps(tool_input)) > 400 else ''}\n```"
        )

    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    desc_parts.append(f"**Time:** {timestamp}")

    embed["description"] = "\n".join(desc_parts)

    return embed


def format_post_tool_use(event_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Format PostToolUse event with execution results."""
    tool_name = event_data.get("tool_name", "Unknown")
    tool_input = event_data.get("tool_input", {})
    tool_response = event_data.get("tool_response", {})
    emoji = TOOL_EMOJIS.get(tool_name, "⚡")

    embed = {"title": f"Completed: {emoji} {tool_name}"}

    # Build detailed description
    desc_parts = []

    # Add session info
    desc_parts.append(f"**Session:** `{session_id}`")

    # Add tool context
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        if len(command) > 100:
            command = command[:97] + "..."
        desc_parts.append(f"**Command:** `{command}`")

        # Add execution results
        stdout = tool_response.get("stdout", "").strip()
        stderr = tool_response.get("stderr", "").strip()
        interrupted = tool_response.get("interrupted", False)

        if stdout:
            # Truncate long output
            if len(stdout) > 500:
                stdout = stdout[:497] + "..."
            desc_parts.append(f"**Output:**\n```\n{stdout}\n```")
        if stderr:
            if len(stderr) > 300:
                stderr = stderr[:297] + "..."
            desc_parts.append(f"**Error:**\n```\n{stderr}\n```")
        if interrupted:
            desc_parts.append("**Status:** ⚠️ Interrupted")

    elif tool_name in ["Read", "Glob", "Grep", "LS"]:
        # For read operations, show summary of results
        if tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            try:
                file_path = Path(file_path).relative_to(Path.cwd())
            except:
                file_path = Path(file_path).name
            desc_parts.append(f"**File:** `{file_path}`")

            # Check if response is string (file content) or dict
            if isinstance(tool_response, str):
                lines = tool_response.count("\n") + 1
                desc_parts.append(f"**Lines read:** {lines}")
            elif isinstance(tool_response, dict) and tool_response.get("error"):
                desc_parts.append(f"**Error:** {tool_response['error']}")

        elif tool_name in ["Glob", "Grep", "LS"]:
            # These typically return lists or file counts
            if isinstance(tool_response, list):
                desc_parts.append(f"**Results found:** {len(tool_response)}")
                # Show first few results
                if tool_response:
                    preview = tool_response[:5]
                    preview_str = "\n".join(f"  • `{item}`" for item in preview)
                    desc_parts.append(f"**Preview:**\n{preview_str}")
                    if len(tool_response) > 5:
                        desc_parts.append(f"  *... and {len(tool_response) - 5} more*")
            elif isinstance(tool_response, str):
                # For text responses, show line count
                lines = (
                    tool_response.strip().split("\n") if tool_response.strip() else []
                )
                desc_parts.append(f"**Results found:** {len(lines)}")

    elif tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = tool_input.get("file_path", "")
        try:
            file_path = Path(file_path).relative_to(Path.cwd())
        except:
            file_path = Path(file_path).name
        desc_parts.append(f"**File:** `{file_path}`")

        # Check for success/error in response
        if isinstance(tool_response, dict):
            if tool_response.get("success"):
                desc_parts.append("**Status:** ✅ Success")
            elif tool_response.get("error"):
                desc_parts.append(f"**Error:** {tool_response['error']}")
        elif isinstance(tool_response, str) and "error" in tool_response.lower():
            desc_parts.append(f"**Error:** {tool_response[:200]}")
        else:
            desc_parts.append("**Status:** ✅ Completed")

    elif tool_name == "Task":
        # For subagent tasks, show summary
        desc = tool_input.get("description", "")
        if desc:
            desc_parts.append(f"**Task:** {desc}")

        # Show response summary
        if isinstance(tool_response, str):
            summary = tool_response[:300]
            if len(tool_response) > 300:
                summary += "..."
            desc_parts.append(f"**Result:**\n{summary}")

    elif tool_name == "WebFetch":
        url = tool_input.get("url", "")
        desc_parts.append(f"**URL:** `{url}`")

        # Show fetch result summary
        if isinstance(tool_response, str):
            if "error" in tool_response.lower():
                desc_parts.append(f"**Error:** {tool_response[:200]}")
            else:
                desc_parts.append(f"**Content length:** {len(tool_response)} chars")

    else:
        # For unknown tools, show response summary
        if isinstance(tool_response, dict):
            response_str = json.dumps(tool_response, indent=2)[:300]
            desc_parts.append(
                f"**Response:**\n```json\n{response_str}{' ...' if len(json.dumps(tool_response)) > 300 else ''}\n```"
            )
        elif isinstance(tool_response, str):
            response_str = tool_response[:300]
            desc_parts.append(
                f"**Response:** {response_str}{' ...' if len(tool_response) > 300 else ''}"
            )

    # Add execution time if available
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    desc_parts.append(f"**Completed at:** {timestamp}")

    embed["description"] = "\n".join(desc_parts)

    return embed


def format_notification(event_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
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
                value_str = json.dumps(value, indent=2)[:200]
                desc_parts.append(
                    f"**{key.title()}:**\n```json\n{value_str}{' ...' if len(json.dumps(value)) > 200 else ''}\n```"
                )

    return {"title": "📢 Notification", "description": "\n".join(desc_parts)}


def format_stop(event_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
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


def format_subagent_stop(event_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
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
            result_summary = result[:400]
            if len(result) > 400:
                result_summary += "..."
            desc_parts.append(f"**Result:**\n{result_summary}")
        else:
            result_str = json.dumps(result, indent=2)[:400]
            desc_parts.append(
                f"**Result:**\n```json\n{result_str}{' ...' if len(json.dumps(result)) > 400 else ''}\n```"
            )

    # Add execution stats if available
    for key in ["execution_time", "tools_used", "status"]:
        if key in event_data:
            desc_parts.append(f"**{key.replace('_', ' ').title()}:** {event_data[key]}")

    return {"title": "🤖 Subagent Completed", "description": "\n".join(desc_parts)}


def format_default(
    event_type: str, event_data: Dict[str, Any], session_id: str
) -> Dict[str, Any]:
    """Format unknown event types."""
    return {"title": f"⚡ {event_type}", "description": "Unknown event type"}


# Event formatter dispatch table
EVENT_FORMATTERS = {
    "PreToolUse": format_pre_tool_use,
    "PostToolUse": format_post_tool_use,
    "Notification": format_notification,
    "Stop": format_stop,
    "SubagentStop": format_subagent_stop,
}


def format_event(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format Claude Code event into Discord embed with length limits."""
    timestamp = datetime.now().isoformat()
    session_id = event_data.get("session_id", "unknown")[:8]

    # Get formatter for event type
    formatter = EVENT_FORMATTERS.get(event_type)
    if formatter:
        embed = formatter(event_data, session_id)
    else:
        embed = format_default(event_type, event_data, session_id)

    # Enforce Discord's length limits
    if "title" in embed and len(embed["title"]) > MAX_TITLE_LENGTH:
        embed["title"] = embed["title"][: MAX_TITLE_LENGTH - 3] + "..."

    if "description" in embed and len(embed["description"]) > MAX_DESCRIPTION_LENGTH:
        embed["description"] = (
            embed["description"][: MAX_DESCRIPTION_LENGTH - 3] + "..."
        )

    # Add common fields
    embed["timestamp"] = timestamp
    embed["color"] = EVENT_COLORS.get(event_type, 0x808080)
    embed["footer"] = {"text": f"Session: {session_id} | Event: {event_type}"}

    return {"embeds": [embed]}


def send_to_discord(
    message: Dict[str, Any], config: Dict[str, str], logger: logging.Logger
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

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.error(f"Webhook failed: {e}")

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

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            logger.error(f"Bot API failed: {e}")

    return False


def main():
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

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error(f"Error processing event data: {e}")
    except Exception as e:
        # Catch any other unexpected errors to ensure we don't block Claude Code
        logger.error(f"Unexpected error: {e}")

    # Always exit 0 to not block Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
