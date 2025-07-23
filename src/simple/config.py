#!/usr/bin/env python3
"""Simple configuration loading for Discord Event Notifier.

This module provides clean configuration management with a focus on
simplicity and ease of use.
"""

import os
from pathlib import Path

from event_types import ChannelMapping, ChannelRouting, Config

from utils import parse_bool

# Python 3.13+ required - pure standard library

# Official Claude Code event routing (1:1 mapping to dedicated channels)
DEFAULT_EVENT_ROUTING = {
    "PreToolUse": "pretooluse",
    "PostToolUse": "posttooluse", 
    "Notification": "notification",
    "UserPromptSubmit": "userpromptsubmit",
    "Stop": "stop",
    "SubagentStop": "subagentstop",
    "PreCompact": "precompact",
}

# Tool-specific routing can override event routing
DEFAULT_TOOL_ROUTING = {
    # Tools will be added as needed (枝番 sub-numbers)
    # For now, all tools go through their respective event channels
}


def load_config() -> Config:
    """Load configuration from environment and .env file.

    Priority order:
    1. Environment variables (highest)
    2. ~/.claude/.env file
    3. Default values (lowest)

    Returns:
        Config dictionary with all settings
    """
    config: Config = {}

    # Load .env file if exists
    env_file = Path.home() / ".claude" / ".env"
    if env_file.exists():
        _load_env_file(env_file, config)

    # Override with environment variables
    _load_from_env(config)

    # Validate credentials
    if not _has_valid_credentials(config):
        # Return empty config - gracefully exit without Discord
        return {}

    # Validate thread feature dependencies
    _validate_thread_config(config)

    return config


def _load_env_file(env_file: Path, config: Config) -> None:
    """Load configuration from .env file."""
    try:
        # Validate that the file path is within expected directories for security
        claude_dir = Path.home() / ".claude"
        try:
            # Resolve both paths to absolute paths and check if env_file is within claude_dir
            env_file_resolved = env_file.resolve(strict=True)
            claude_dir_resolved = claude_dir.resolve(strict=True)

            # Check if the env_file is within the claude directory
            try:
                env_file_resolved.relative_to(claude_dir_resolved)
            except ValueError:
                # File is not within the .claude directory, skip loading
                return
        except OSError:
            # File doesn't exist or can't be resolved, skip loading
            return

        with env_file.open() as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    _set_config_value(config, key.strip(), value.strip())
    except OSError:
        # Silently ignore file access errors
        pass
    except UnicodeDecodeError:
        # Silently ignore encoding errors
        pass


def _load_from_env(config: Config) -> None:
    """Load configuration from environment variables."""
    # Discord credentials
    if val := os.environ.get("DISCORD_WEBHOOK_URL"):
        config["webhook_url"] = val
    if val := os.environ.get("DISCORD_BOT_TOKEN"):
        config["bot_token"] = val
    if val := os.environ.get("DISCORD_CHANNEL_ID"):
        config["channel_id"] = val

    # Features
    if val := os.environ.get("DISCORD_USE_THREADS"):
        config["use_threads"] = parse_bool(val)
    if val := os.environ.get("DISCORD_THREAD_FOR_TASK"):
        config["thread_for_task"] = parse_bool(val)
    if val := os.environ.get("DISCORD_MENTION_USER_ID"):
        config["mention_user_id"] = val
    if val := os.environ.get("DISCORD_DEBUG"):
        config["debug"] = parse_bool(val)

    # Individual event control (new style - prioritized)
    event_states = {}
    if val := os.environ.get("DISCORD_EVENT_PRETOOLUSE"):
        event_states["PreToolUse"] = parse_bool(val)
    if val := os.environ.get("DISCORD_EVENT_POSTTOOLUSE"):
        event_states["PostToolUse"] = parse_bool(val)
    if val := os.environ.get("DISCORD_EVENT_NOTIFICATION"):
        event_states["Notification"] = parse_bool(val)
    if val := os.environ.get("DISCORD_EVENT_STOP"):
        event_states["Stop"] = parse_bool(val)
    if val := os.environ.get("DISCORD_EVENT_SUBAGENT_STOP"):
        event_states["SubagentStop"] = parse_bool(val)
    if event_states:
        config["event_states"] = event_states

    # Individual tool control (new style - prioritized)
    tool_states = {}
    if val := os.environ.get("DISCORD_TOOL_READ"):
        tool_states["Read"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_EDIT"):
        tool_states["Edit"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_WRITE"):
        tool_states["Write"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_MULTIEDIT"):
        tool_states["MultiEdit"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_TODOWRITE"):
        tool_states["TodoWrite"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_GREP"):
        tool_states["Grep"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_GLOB"):
        tool_states["Glob"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_LS"):
        tool_states["LS"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_BASH"):
        tool_states["Bash"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_TASK"):
        tool_states["Task"] = parse_bool(val)
    if val := os.environ.get("DISCORD_TOOL_WEBFETCH"):
        tool_states["WebFetch"] = parse_bool(val)
    if tool_states:
        config["tool_states"] = tool_states

    # Legacy event filtering (fallback only if new style not set)
    if "event_states" not in config:
        if val := os.environ.get("DISCORD_ENABLED_EVENTS"):
            config["enabled_events"] = [e.strip() for e in val.split(",") if e.strip()]
        if val := os.environ.get("DISCORD_DISABLED_EVENTS"):
            config["disabled_events"] = [e.strip() for e in val.split(",") if e.strip()]

    # Legacy tool filtering (fallback only if new style not set)
    if "tool_states" not in config:
        if val := os.environ.get("DISCORD_DISABLED_TOOLS"):
            config["disabled_tools"] = [t.strip() for t in val.split(",") if t.strip()]

    # Channel routing configuration
    _load_channel_routing_from_env(config)


def _load_channel_routing_from_env(config: Config) -> None:
    """Load channel routing configuration from environment variables."""
    routing: ChannelRouting = {}
    channels: ChannelMapping = {}

    # Official Claude Code events (1:1 mapping)
    if val := os.environ.get("DISCORD_CHANNEL_PRETOOLUSE"):
        channels["pretooluse"] = val
    if val := os.environ.get("DISCORD_CHANNEL_POSTTOOLUSE"):
        channels["posttooluse"] = val
    if val := os.environ.get("DISCORD_CHANNEL_NOTIFICATION"):
        channels["notification"] = val
    if val := os.environ.get("DISCORD_CHANNEL_USERPROMPTSUBMIT"):
        channels["userpromptsubmit"] = val
    if val := os.environ.get("DISCORD_CHANNEL_STOP"):
        channels["stop"] = val
    if val := os.environ.get("DISCORD_CHANNEL_SUBAGENTSTOP"):
        channels["subagentstop"] = val
    if val := os.environ.get("DISCORD_CHANNEL_PRECOMPACT"):
        channels["precompact"] = val
    if val := os.environ.get("DISCORD_CHANNEL_DEFAULT"):
        channels["default"] = val

    # Enable routing if any channels are configured
    if channels:
        routing["enabled"] = True
        routing["channels"] = channels

        # Default routing rules using module constants
        routing["event_routing"] = DEFAULT_EVENT_ROUTING.copy()
        routing["tool_routing"] = DEFAULT_TOOL_ROUTING.copy()

        config["channel_routing"] = routing


def _set_config_value(config: Config, key: str, value: str) -> None:
    """Set configuration value from .env file."""
    if key == "DISCORD_WEBHOOK_URL":
        config["webhook_url"] = value
    elif key == "DISCORD_BOT_TOKEN":
        config["bot_token"] = value
    elif key == "DISCORD_CHANNEL_ID":
        config["channel_id"] = value
    elif key == "DISCORD_USE_THREADS":
        config["use_threads"] = parse_bool(value)
    elif key == "DISCORD_THREAD_FOR_TASK":
        config["thread_for_task"] = parse_bool(value)
    elif key == "DISCORD_MENTION_USER_ID":
        config["mention_user_id"] = value
    elif key == "DISCORD_DEBUG":
        config["debug"] = parse_bool(value)

    # Individual event control (new style - highest priority)
    elif key == "DISCORD_EVENT_PRETOOLUSE":
        if "event_states" not in config:
            config["event_states"] = {}
        config["event_states"]["PreToolUse"] = parse_bool(value)
    elif key == "DISCORD_EVENT_POSTTOOLUSE":
        if "event_states" not in config:
            config["event_states"] = {}
        config["event_states"]["PostToolUse"] = parse_bool(value)
    elif key == "DISCORD_EVENT_NOTIFICATION":
        if "event_states" not in config:
            config["event_states"] = {}
        config["event_states"]["Notification"] = parse_bool(value)
    elif key == "DISCORD_EVENT_STOP":
        if "event_states" not in config:
            config["event_states"] = {}
        config["event_states"]["Stop"] = parse_bool(value)
    elif key == "DISCORD_EVENT_SUBAGENT_STOP":
        if "event_states" not in config:
            config["event_states"] = {}
        config["event_states"]["SubagentStop"] = parse_bool(value)

    # Individual tool control (new style - highest priority)
    elif key == "DISCORD_TOOL_READ":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Read"] = parse_bool(value)
    elif key == "DISCORD_TOOL_EDIT":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Edit"] = parse_bool(value)
    elif key == "DISCORD_TOOL_WRITE":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Write"] = parse_bool(value)
    elif key == "DISCORD_TOOL_MULTIEDIT":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["MultiEdit"] = parse_bool(value)
    elif key == "DISCORD_TOOL_TODOWRITE":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["TodoWrite"] = parse_bool(value)
    elif key == "DISCORD_TOOL_GREP":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Grep"] = parse_bool(value)
    elif key == "DISCORD_TOOL_GLOB":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Glob"] = parse_bool(value)
    elif key == "DISCORD_TOOL_LS":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["LS"] = parse_bool(value)
    elif key == "DISCORD_TOOL_BASH":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Bash"] = parse_bool(value)
    elif key == "DISCORD_TOOL_TASK":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["Task"] = parse_bool(value)
    elif key == "DISCORD_TOOL_WEBFETCH":
        if "tool_states" not in config:
            config["tool_states"] = {}
        config["tool_states"]["WebFetch"] = parse_bool(value)

    # Channel routing settings
    elif key.startswith("DISCORD_CHANNEL_"):
        _set_channel_config_value(config, key, value)

    # Legacy settings (only loaded if new style not already set)
    elif key == "DISCORD_ENABLED_EVENTS" and "event_states" not in config:
        config["enabled_events"] = [e.strip() for e in value.split(",") if e.strip()]
    elif key == "DISCORD_DISABLED_EVENTS" and "event_states" not in config:
        config["disabled_events"] = [e.strip() for e in value.split(",") if e.strip()]
    elif key == "DISCORD_DISABLED_TOOLS" and "tool_states" not in config:
        config["disabled_tools"] = [t.strip() for t in value.split(",") if t.strip()]


def _set_channel_config_value(config: Config, key: str, value: str) -> None:
    """Set channel routing configuration value from .env file."""
    # Initialize routing structure if not exists
    if "channel_routing" not in config:
        config["channel_routing"] = {}
    if "channels" not in config["channel_routing"]:
        config["channel_routing"]["channels"] = {}

    routing = config["channel_routing"]
    channels = routing["channels"]

    # Official Claude Code event channels
    if key == "DISCORD_CHANNEL_PRETOOLUSE":
        channels["pretooluse"] = value
    elif key == "DISCORD_CHANNEL_POSTTOOLUSE":
        channels["posttooluse"] = value
    elif key == "DISCORD_CHANNEL_NOTIFICATION":
        channels["notification"] = value
    elif key == "DISCORD_CHANNEL_USERPROMPTSUBMIT":
        channels["userpromptsubmit"] = value
    elif key == "DISCORD_CHANNEL_STOP":
        channels["stop"] = value
    elif key == "DISCORD_CHANNEL_SUBAGENTSTOP":
        channels["subagentstop"] = value
    elif key == "DISCORD_CHANNEL_PRECOMPACT":
        channels["precompact"] = value
    elif key == "DISCORD_CHANNEL_DEFAULT":
        channels["default"] = value

    # Set routing as enabled and add default routing rules
    if channels:
        routing["enabled"] = True
        routing["event_routing"] = DEFAULT_EVENT_ROUTING.copy()
        routing["tool_routing"] = DEFAULT_TOOL_ROUTING.copy()


def get_channel_for_event(event_name: str, tool_name: str | None, config: Config) -> str | None:
    """Get the appropriate channel ID for an event.

    Args:
        event_name: Claude Code event name (PreToolUse, PostToolUse, etc.)
        tool_name: Tool name if applicable
        config: Configuration dictionary

    Returns:
        Channel ID if routing is enabled and channel exists, None otherwise
    """
    routing = config.get("channel_routing")
    if not routing or not routing.get("enabled"):
        return None

    channels = routing.get("channels", {})
    if not channels:
        return None

    # Try tool-specific routing first if tool_name provided
    if tool_name:
        tool_routing = routing.get("tool_routing", {})
        if tool_name in tool_routing:
            channel_key = tool_routing[tool_name]
            if channel_key in channels:
                return channels[channel_key]

    # Fall back to event routing
    event_routing = routing.get("event_routing", {})
    if event_name in event_routing:
        channel_key = event_routing[event_name]
        if channel_key in channels:
            return channels[channel_key]

    # Final fallback to default channel
    return channels.get("default")


def has_channel_routing(config: Config) -> bool:
    """Check if channel routing is enabled and configured.

    Args:
        config: Configuration dictionary

    Returns:
        True if channel routing is enabled with channels configured
    """
    routing = config.get("channel_routing")
    if not routing or not routing.get("enabled"):
        return False

    channels = routing.get("channels", {})
    return bool(channels)


def _has_valid_credentials(config: Config) -> bool:
    """Check if we have valid Discord credentials."""
    # Need either webhook URL or (bot token + channel ID)
    has_webhook = bool(config.get("webhook_url"))
    has_bot = bool(config.get("bot_token") and config.get("channel_id"))
    return has_webhook or has_bot


def _validate_thread_config(config: Config) -> None:
    """Validate thread feature dependencies and disable if required settings are missing."""
    import logging

    logger = logging.getLogger(__name__)

    # Check if thread features are enabled
    thread_for_task = config.get("thread_for_task", False)
    use_threads = config.get("use_threads", False)

    if thread_for_task or use_threads:
        # Thread features require bot token and channel ID (webhooks don't support threads)
        if not (config.get("bot_token") and config.get("channel_id")):
            logger.warning(
                "Thread features are enabled but bot_token and channel_id are not configured. "
                "Disabling thread features. Please set DISCORD_BOT_TOKEN and DISCORD_CHANNEL_ID."
            )
            # Disable thread features to prevent runtime errors
            config["thread_for_task"] = False
            config["use_threads"] = False
