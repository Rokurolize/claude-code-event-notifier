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
    """Load Discord configuration from environment or .env.discord file."""
    config = {
        "webhook_url": os.environ.get("DISCORD_WEBHOOK_URL"),
        "bot_token": os.environ.get("DISCORD_TOKEN"),
        "channel_id": os.environ.get("DISCORD_CHANNEL_ID"),
        "debug": os.environ.get("DISCORD_DEBUG", "0") == "1",
    }

    # Load from .env.discord if needed
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    if env_file.exists() and not all([config["webhook_url"], config["bot_token"]]):
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        value = value.strip('"').strip("'")

                        if key == "DISCORD_WEBHOOK_URL" and not config["webhook_url"]:
                            config["webhook_url"] = value
                        elif key == "DISCORD_TOKEN" and not config["bot_token"]:
                            config["bot_token"] = value
                        elif key == "DISCORD_CHANNEL_ID" and not config["channel_id"]:
                            config["channel_id"] = value
                        elif key == "DISCORD_DEBUG":
                            config["debug"] = value == "1"
        except Exception as e:
            print(f"Error reading {env_file}: {e}", file=sys.stderr)
            sys.exit(1)

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


def format_event(event_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Format Claude Code event into Discord embed."""
    timestamp = datetime.now().isoformat()
    session_id = event_data.get("session_id", "unknown")[:8]

    embed = {
        "timestamp": timestamp,
        "color": EVENT_COLORS.get(event_type, 0x808080),
        "footer": {"text": f"Session: {session_id}"},
    }

    if event_type == "PreToolUse":
        tool_name = event_data.get("tool_name", "Unknown")
        tool_input = event_data.get("tool_input", {})
        emoji = TOOL_EMOJIS.get(tool_name, "⚡")

        embed["title"] = f"About to execute: {emoji} {tool_name}"

        # Add tool-specific details
        if tool_name == "Bash":
            command = tool_input.get("command", "")[:100]
            if len(tool_input.get("command", "")) > 100:
                command += "..."
            embed["description"] = f"**Command:** `{command}`"
        elif tool_name in ["Write", "Edit", "MultiEdit", "Read"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                # Show relative path if possible
                try:
                    file_path = Path(file_path).relative_to(Path.cwd())
                except:
                    file_path = Path(file_path).name
                embed["description"] = f"**File:** `{file_path}`"
        elif tool_name in ["Glob", "Grep"]:
            pattern = tool_input.get("pattern", "")
            embed["description"] = f"**Pattern:** `{pattern}`"

    elif event_type == "PostToolUse":
        tool_name = event_data.get("tool_name", "Unknown")
        emoji = TOOL_EMOJIS.get(tool_name, "⚡")
        embed["title"] = f"Completed: {emoji} {tool_name}"
        embed["description"] = "Tool execution finished"

    elif event_type == "Notification":
        embed["title"] = "📢 Notification"
        embed["description"] = event_data.get("message", "System notification")

    elif event_type == "Stop":
        embed["title"] = "🏁 Session Ended"
        embed["description"] = f"Claude Code session `{session_id}` has finished"

    elif event_type == "SubagentStop":
        embed["title"] = "🤖 Subagent Completed"
        embed["description"] = f"Subagent task completed in session `{session_id}`"

    else:
        embed["title"] = f"⚡ {event_type}"
        embed["description"] = "Unknown event type"

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
                headers={"Content-Type": "application/json"},
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.debug(f"Webhook response: {response.status}")
                return response.status == 204

        except Exception as e:
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
                },
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                logger.debug(f"Bot API response: {response.status}")
                return 200 <= response.status < 300

        except Exception as e:
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

    except Exception as e:
        logger.error(f"Error: {e}")

    # Always exit 0 to not block Claude Code
    sys.exit(0)


if __name__ == "__main__":
    main()
