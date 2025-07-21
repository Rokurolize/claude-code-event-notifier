#!/usr/bin/env python3
"""Simple configuration loading for Discord Event Notifier.

This module provides clean configuration management with a focus on
simplicity and ease of use.
"""

import os
from pathlib import Path
from typing import cast

from event_types import Config
from utils import parse_bool

# Python 3.13+ required - pure standard library


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
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    _set_config_value(config, key.strip(), value.strip())
    except (IOError, OSError):
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
    
    # Legacy settings (only loaded if new style not already set)
    elif key == "DISCORD_ENABLED_EVENTS" and "event_states" not in config:
        config["enabled_events"] = [e.strip() for e in value.split(",") if e.strip()]
    elif key == "DISCORD_DISABLED_EVENTS" and "event_states" not in config:
        config["disabled_events"] = [e.strip() for e in value.split(",") if e.strip()]
    elif key == "DISCORD_DISABLED_TOOLS" and "tool_states" not in config:
        config["disabled_tools"] = [t.strip() for t in value.split(",") if t.strip()]



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