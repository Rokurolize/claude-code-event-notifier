#!/usr/bin/env python3
"""
Discord Event Logger for Claude Code Hooks - With Debug Logging

This script receives Claude Code hook events via stdin and posts
human-readable summaries to a Discord channel using a webhook.

Usage: Called automatically by Claude Code hooks system
       Can be run with --debug flag for detailed logging

Environment Variables:
- DISCORD_WEBHOOK_URL: Discord webhook URL for posting messages
- DISCORD_TOKEN: Discord bot token (fallback if webhook fails)
- DISCORD_CHANNEL_ID: Channel ID for bot posting (fallback)
- DISCORD_DEBUG: Set to "1" to enable debug logging
"""

import argparse
import json
import logging
import os
import sys
import traceback
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# Setup logging configuration
def setup_logging(debug=False):
    """Configure logging with optional debug mode."""
    log_dir = Path("/home/ubuntu/.claude/hooks/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create log filename with date
    log_file = log_dir / f"discord_hook_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Configure logging format
    log_format = "%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"

    # Set up both file and console logging
    handlers = []

    # File handler - always logs at DEBUG level
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(file_handler)

    # Console handler - only for errors unless debug mode
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if debug else logging.ERROR)
    console_handler.setFormatter(logging.Formatter(log_format))
    handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(level=logging.DEBUG, handlers=handlers)

    return logging.getLogger(__name__)


# Global logger instance
logger = None


def get_discord_config():
    """Get Discord configuration from environment or .env file."""
    logger.debug("Starting Discord configuration retrieval")
    config = {}

    # Try environment variables first
    config["webhook_url"] = os.environ.get("DISCORD_WEBHOOK_URL")
    config["bot_token"] = os.environ.get("DISCORD_TOKEN")
    config["channel_id"] = os.environ.get("DISCORD_CHANNEL_ID")

    logger.debug(
        f"Environment variables loaded: webhook_url={bool(config['webhook_url'])}, bot_token={bool(config['bot_token'])}, channel_id={config['channel_id']}"
    )

    # Primary configuration file in secure hooks directory (absolute path)
    secure_env_file = Path("/home/ubuntu/.claude/hooks/.env.discord")

    # Try loading from secure .env.discord file first
    if not all(config.values()) and secure_env_file.exists():
        logger.debug(f"Loading config from {secure_env_file}")
        try:
            with open(secure_env_file) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        # Remove quotes if present
                        value = value.strip('"').strip("'")

                        if key == "DISCORD_WEBHOOK_URL" and not config["webhook_url"]:
                            config["webhook_url"] = value
                            logger.debug(f"Loaded webhook URL from .env.discord")
                        elif key == "DISCORD_TOKEN" and not config["bot_token"]:
                            config["bot_token"] = value
                            logger.debug(f"Loaded bot token from .env.discord")
                        elif key == "DISCORD_CHANNEL_ID" and not config["channel_id"]:
                            config["channel_id"] = value
                            logger.debug(
                                f"Loaded channel ID from .env.discord: {value}"
                            )
        except Exception as e:
            logger.error(f"Error reading {secure_env_file}: {e}")
    else:
        logger.debug(
            f".env.discord exists: {secure_env_file.exists()}, all config values: {all(config.values())}"
        )

    # Fallback to other locations if still not configured
    if not all(config.values()):
        possible_env_files = [
            Path.home() / "human-in-the-loop" / ".env.test",  # Project directory
            Path.cwd() / ".env.test",  # Current working directory
        ]

        for env_file in possible_env_files:
            if env_file.exists():
                logger.debug(f"Trying fallback config from {env_file}")
                try:
                    with open(env_file) as f:
                        for line in f:
                            if "=" in line and not line.startswith("#"):
                                key, value = line.strip().split("=", 1)
                                value = value.strip('"').strip("'")

                                if key == "DISCORD_TOKEN" and not config["bot_token"]:
                                    config["bot_token"] = value
                                    logger.debug(f"Loaded bot token from {env_file}")
                                elif (
                                    key == "DISCORD_CHANNEL_ID"
                                    and not config["channel_id"]
                                ):
                                    config["channel_id"] = value
                                    logger.debug(
                                        f"Loaded channel ID from {env_file}: {value}"
                                    )
                                elif (
                                    key == "DISCORD_WEBHOOK_URL"
                                    and not config["webhook_url"]
                                ):
                                    config["webhook_url"] = value
                                    logger.debug(f"Loaded webhook URL from {env_file}")
                    if all(config.values()):
                        logger.info(f"All config loaded from {env_file}")
                        break  # Found all needed config
                except Exception as e:
                    logger.error(f"Error reading {env_file}: {e}")

    # Log final configuration status
    logger.info(
        f"Final config status: webhook_url={bool(config['webhook_url'])}, bot_token={bool(config['bot_token'])}, channel_id={config['channel_id']}"
    )

    return config


def format_tool_name(tool_name):
    """Format tool name with appropriate emoji."""
    emoji_map = {
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
    formatted = f"{emoji_map.get(tool_name, '⚡')} {tool_name}"
    logger.debug(f"Formatted tool name: {tool_name} -> {formatted}")
    return formatted


def format_file_path(path):
    """Format file path for display, showing only relevant parts."""
    if not path:
        return ""

    path_obj = Path(path)

    # Show relative path if in current directory
    try:
        rel_path = path_obj.relative_to(Path.cwd())
        if len(str(rel_path)) < len(str(path_obj)):
            formatted = f"`{rel_path}`"
            logger.debug(f"Formatted path as relative: {path} -> {formatted}")
            return formatted
    except ValueError:
        pass

    # Show just filename for long paths
    if len(str(path_obj)) > 50:
        formatted = f"`.../{path_obj.name}`"
        logger.debug(f"Formatted long path: {path} -> {formatted}")
        return formatted

    formatted = f"`{path_obj}`"
    logger.debug(f"Formatted path: {path} -> {formatted}")
    return formatted


def create_embed_message(event_type, hook_data):
    """Create a Discord embed message for the hook event."""
    logger.debug(f"Creating embed for event_type: {event_type}")
    logger.debug(f"Hook data keys: {list(hook_data.keys())}")

    timestamp = datetime.now().isoformat()
    session_id = hook_data.get("session_id", "unknown")[:8]

    # Base embed structure
    embed = {"timestamp": timestamp, "footer": {"text": f"Session: {session_id}"}}

    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})

    logger.debug(
        f"Tool name: {tool_name}, Tool input keys: {list(tool_input.keys()) if isinstance(tool_input, dict) else 'not a dict'}"
    )

    if event_type == "PreToolUse":
        embed.update(
            {
                "title": f"About to execute: {format_tool_name(tool_name)}",
                "color": 0x3498DB,  # Blue
            }
        )

        description_parts = []

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            description_parts.append(
                f"**Command:** `{command[:100]}{'...' if len(command) > 100 else ''}`"
            )
            logger.debug(f"Bash command: {command[:50]}...")

        elif tool_name in ["Write", "Edit", "MultiEdit"]:
            file_path = tool_input.get("file_path", "")
            if file_path:
                description_parts.append(f"**File:** {format_file_path(file_path)}")

            if tool_name == "Write":
                content = tool_input.get("content", "")
                if content:
                    lines = len(content.split("\n"))
                    chars = len(content)
                    description_parts.append(
                        f"**Content:** {lines} lines, {chars} characters"
                    )
                    logger.debug(f"Write content: {lines} lines, {chars} chars")

        elif tool_name == "Read":
            file_path = tool_input.get("file_path", "")
            if file_path:
                description_parts.append(f"**Reading:** {format_file_path(file_path)}")

        elif tool_name in ["Glob", "Grep"]:
            pattern = tool_input.get("pattern", "")
            if pattern:
                description_parts.append(f"**Pattern:** `{pattern}`")

        elif tool_name == "mcp__human-in-the-loop__ask_human":
            question = tool_input.get("question", "")
            if question:
                preview = question[:100] + "..." if len(question) > 100 else question
                description_parts.append(f"**Question:** {preview}")

        embed["description"] = (
            "\n".join(description_parts) if description_parts else "Executing tool..."
        )

    elif event_type == "PostToolUse":
        embed.update(
            {
                "title": f"Completed: {format_tool_name(tool_name)}",
                "color": 0x2ECC71,  # Green
                "description": "Tool execution finished",
            }
        )

        # Add execution time if available
        if "execution_time" in hook_data:
            embed["description"] += f" in {hook_data['execution_time']:.2f}s"

    elif event_type == "Notification":
        embed.update(
            {
                "title": "📢 Notification",
                "color": 0xF39C12,  # Orange
                "description": hook_data.get("message", "System notification"),
            }
        )

    elif event_type == "Stop":
        embed.update(
            {
                "title": "🏁 Session Ended",
                "color": 0x95A5A6,  # Gray
                "description": f"Claude Code session `{session_id}` has finished",
            }
        )

    elif event_type == "SubagentStop":
        embed.update(
            {
                "title": "🤖 Subagent Completed",
                "color": 0x9B59B6,  # Purple
                "description": f"Subagent task completed in session `{session_id}`",
            }
        )

    logger.debug(f"Created embed: {embed}")
    return {"embeds": [embed]}


def send_to_discord_webhook(webhook_url, message_data):
    """Send message to Discord via webhook."""
    logger.info(f"Attempting to send via webhook: {webhook_url[:50]}...")
    logger.debug(f"Message data: {json.dumps(message_data, indent=2)}")

    try:
        data = json.dumps(message_data).encode("utf-8")
        req = urllib.request.Request(
            webhook_url, data=data, headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            logger.info(f"Webhook response status: {response.status}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            return response.status == 204
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error {e.code}: {e.reason}")
        logger.debug(f"Error response: {e.read().decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        logger.error(f"Webhook error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return False


def send_to_discord_bot(bot_token, channel_id, message_data):
    """Send message to Discord via bot API (fallback)."""
    logger.info(f"Attempting to send via bot API to channel: {channel_id}")
    logger.debug(f"Using bot token: {bot_token[:10]}...")

    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        data = json.dumps(message_data).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            logger.info(f"Bot API response status: {response.status}")
            response_data = response.read().decode("utf-8")
            logger.debug(f"Response data: {response_data}")
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        logger.error(f"HTTP Error {e.code}: {e.reason}")
        logger.debug(f"Error response: {e.read().decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        logger.error(f"Bot API error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        return False


def main():
    """Main function to process hook input and send to Discord."""
    global logger

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Discord Event Logger for Claude Code Hooks"
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging to console"
    )
    args = parser.parse_args()

    # Check for debug environment variable too
    debug_mode = args.debug or os.environ.get("DISCORD_DEBUG") == "1"

    # Setup logging
    logger = setup_logging(debug=debug_mode)
    logger.info("=" * 60)
    logger.info("Discord Event Logger Started")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Script location: {__file__}")

    try:
        # Read JSON input from stdin
        logger.debug("Reading JSON from stdin...")
        try:
            raw_input = sys.stdin.read()
            logger.debug(f"Raw input length: {len(raw_input)} chars")
            logger.debug(f"Raw input preview: {raw_input[:200]}...")

            hook_data = json.loads(raw_input)
            logger.info(f"Successfully parsed JSON with keys: {list(hook_data.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON input: {e}")
            logger.debug(f"Failed to parse: {raw_input[:500]}")
            sys.exit(1)

        # Determine event type from the calling context
        event_type = os.environ.get("CLAUDE_HOOK_EVENT", "Unknown")
        logger.info(f"Event type: {event_type}")

        # Get Discord configuration
        config = get_discord_config()

        if not config["webhook_url"] and not (
            config["bot_token"] and config["channel_id"]
        ):
            logger.warning("No Discord configuration found - exiting gracefully")
            sys.exit(0)  # Exit gracefully, don't block Claude

        # Create message
        message_data = create_embed_message(event_type, hook_data)

        # Try webhook first, fallback to bot API
        success = False
        if config["webhook_url"]:
            logger.info("Trying webhook method...")
            success = send_to_discord_webhook(config["webhook_url"], message_data)
            logger.info(f"Webhook result: {'success' if success else 'failed'}")

        if not success and config["bot_token"] and config["channel_id"]:
            logger.info("Trying bot API method...")
            success = send_to_discord_bot(
                config["bot_token"], config["channel_id"], message_data
            )
            logger.info(f"Bot API result: {'success' if success else 'failed'}")

        if not success:
            logger.error("Failed to send Discord notification via any method")
        else:
            logger.info("Discord notification sent successfully!")

        # Always exit 0 to not block Claude Code
        sys.exit(0)

    except Exception as e:
        # Log error but don't block Claude Code
        logger.error(f"Discord logger error: {type(e).__name__}: {e}")
        logger.debug(traceback.format_exc())
        sys.exit(0)


if __name__ == "__main__":
    main()
