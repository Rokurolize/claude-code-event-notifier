#!/usr/bin/env python3
"""Configuration management for Discord Notifier.

This module handles loading and validation of configuration from
environment variables and .env files.
"""

import hashlib
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# Python 3.13+ features - pure standard library, no external dependencies
from typing import Literal, ReadOnly, TypedDict, cast

from .constants import (
    DEFAULT_THREAD_CLEANUP_DAYS,
    DEFAULT_THREAD_PREFIX,
    ENV_BOT_TOKEN,
    ENV_CHANNEL_ID,
    ENV_CHANNEL_TYPE,
    ENV_DEBUG,
    ENV_DISABLED_EVENTS,
    ENV_DISABLED_TOOLS,
    ENV_ENABLED_EVENTS,
    # Individual event controls
    ENV_EVENT_PRETOOLUSE,
    ENV_EVENT_POSTTOOLUSE,
    ENV_EVENT_NOTIFICATION,
    ENV_EVENT_STOP,
    ENV_EVENT_SUBAGENT_STOP,
    # Individual tool controls
    ENV_TOOL_READ,
    ENV_TOOL_EDIT,
    ENV_TOOL_MULTIEDIT,
    ENV_TOOL_TODOWRITE,
    ENV_TOOL_GREP,
    ENV_TOOL_GLOB,
    ENV_TOOL_LS,
    ENV_TOOL_BASH,
    ENV_TOOL_TASK,
    ENV_TOOL_WEBFETCH,
    ENV_MENTION_USER_ID,
    ENV_THREAD_CLEANUP_DAYS,
    ENV_THREAD_PREFIX,
    ENV_THREAD_STORAGE_PATH,
    ENV_USE_THREADS,
    LOG_FORMAT,
    EventTypes,
)
from .exceptions import ConfigurationError


# Configuration TypedDict hierarchy
class DiscordCredentials(TypedDict):
    """Discord authentication credentials."""

    bot_token: ReadOnly[str | None]
    channel_id: ReadOnly[str | None]


class ThreadConfiguration(TypedDict):
    """Thread-specific configuration."""

    use_threads: bool
    channel_type: Literal["text", "forum"]
    thread_prefix: str
    thread_storage_path: ReadOnly[str | None]
    thread_cleanup_days: int


class NotificationConfiguration(TypedDict):
    """Notification-specific configuration."""

    mention_user_id: str | None
    debug: bool


class IndividualEventConfiguration(TypedDict, total=False):
    """Individual event ON/OFF configuration (recommended approach)."""
    
    # Event controls - true=enabled, false=disabled, None=use default
    event_pretooluse: bool | None
    event_posttooluse: bool | None  
    event_notification: bool | None
    event_stop: bool | None
    event_subagent_stop: bool | None


class IndividualToolConfiguration(TypedDict, total=False):
    """Individual tool ON/OFF configuration (recommended approach)."""
    
    # Tool controls - true=enabled, false=disabled, None=use default
    tool_read: bool | None
    tool_edit: bool | None
    tool_multiedit: bool | None
    tool_todowrite: bool | None
    tool_grep: bool | None
    tool_glob: bool | None
    tool_ls: bool | None
    tool_bash: bool | None
    tool_task: bool | None
    tool_webfetch: bool | None


class EventFilterConfiguration(TypedDict):
    """Event filtering configuration."""

    # Legacy filtering (maintained for backward compatibility)
    enabled_events: list[str] | None
    disabled_events: list[str] | None
    disabled_tools: list[str] | None


class Config(
    DiscordCredentials,
    ThreadConfiguration,
    NotificationConfiguration,
    EventFilterConfiguration,
    IndividualEventConfiguration,
    IndividualToolConfiguration,
):
    """Complete configuration combining all aspects."""


def parse_env_file(file_path: Path) -> dict[str, str]:
    """Parse environment file and return key-value pairs.

    Parses .env format files containing KEY=VALUE pairs, with support for
    comments and quoted values. Used to load Discord configuration from
    the project root .env file.

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
        DISCORD_BOT_TOKEN="your_bot_token_here"
        DISCORD_CHANNEL_ID='123456789012345678'
        # Thread settings
        DISCORD_USE_THREADS=1
        ```

    Example Usage:
        >>> env_vars = parse_env_file(Path(".env"))
        >>> bot_token = env_vars.get("DISCORD_BOT_TOKEN")

    Error Handling:
        - IOError: File access issues (permissions, file not found)
        - ValueError: Line parsing issues (malformed KEY=VALUE pairs)
        - Both result in ConfigurationError being raised
    """
    env_vars: dict[str, str] = {}

    try:
        with Path(file_path).open() as f:
            for line in f:
                stripped_line = line.strip()
                if "=" in stripped_line and not stripped_line.startswith("#"):
                    key, value = stripped_line.split("=", 1)
                    value = value.strip('"').strip("'")
                    env_vars[key] = value
    except (OSError, ValueError) as e:
        raise ConfigurationError(f"Error reading {file_path}: {e}") from e

    return env_vars


def is_valid_event_type(event_type: str) -> bool:
    """Check if event type is valid."""
    return event_type in {e.value for e in EventTypes}


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


def parse_tool_list(tool_list_str: str) -> list[str]:
    """Parse comma-separated tool list string into cleaned list.

    Parses environment variable values like "Read,Edit,TodoWrite,Grep" into a list
    of tool name strings. Unlike parse_event_list, this doesn't validate against
    a fixed set of tool names to allow flexibility.

    Args:
        tool_list_str: Comma-separated string of tool names

    Returns:
        List of tool name strings

    Examples:
        >>> parse_tool_list("Read,Edit,TodoWrite")
        ['Read', 'Edit', 'TodoWrite']
        >>> parse_tool_list("")
        []
        >>> parse_tool_list("  Read  ,  Edit  ")
        ['Read', 'Edit']
    """
    if not tool_list_str:
        return []

    # Split and clean up tool names
    tools = [tool.strip() for tool in tool_list_str.split(",")]
    return [tool for tool in tools if tool]  # Remove empty strings


def parse_bool_env(value: str | None) -> bool | None:
    """Parse environment variable string to boolean value.
    
    Converts string values to boolean using flexible parsing rules.
    Returns None if value is None or empty, allowing for default handling.
    
    Args:
        value: Environment variable string value
        
    Returns:
        True, False, or None (for default handling)
        
    Examples:
        >>> parse_bool_env("true")
        True
        >>> parse_bool_env("false") 
        False
        >>> parse_bool_env("1")
        True
        >>> parse_bool_env("0")
        False
        >>> parse_bool_env("")
        None
        >>> parse_bool_env(None)
        None
    """
    if not value:
        return None
        
    lower_value = value.lower().strip()
    
    # Handle common true values
    if lower_value in ("true", "1", "yes", "on", "enabled"):
        return True
        
    # Handle common false values  
    if lower_value in ("false", "0", "no", "off", "disabled"):
        return False
        
    # Invalid value - return None for default handling
    return None


# Common filtering logic for both tools and events
def _should_process_item(
    item_name: str, 
    config: Config, 
    individual_mappings: dict[str, tuple[str, str]], 
    legacy_config_keys: tuple[str, ...],
    default_behavior: str = "include"
) -> bool:
    """Generic filtering logic for tools and events.
    
    Args:
        item_name: Name of the item to check
        config: Configuration dictionary
        individual_mappings: Dict mapping item names to (config_key, env_var_name)
        legacy_config_keys: Tuple of legacy config keys to check in order
        default_behavior: "include" (default allow) or "exclude" (default deny)
    
    Returns:
        bool: True if item should be processed
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 1. Check individual controls first (highest priority)
    if item_name in individual_mappings:
        config_key, env_var_name = individual_mappings[item_name]
        individual_setting = config.get(config_key)
        if individual_setting is not None:
            logger.debug(f"Item {item_name}: Using individual control {env_var_name}={individual_setting} → {individual_setting}")
            return individual_setting
    
    # 2. Check legacy configuration
    for legacy_key in legacy_config_keys:
        legacy_list = config.get(legacy_key)
        if legacy_list:
            if legacy_key.endswith("_enabled") or "enabled" in legacy_key:
                # Whitelist behavior: only included items are processed
                result = item_name in legacy_list
                logger.debug(f"Item {item_name}: Using legacy {legacy_key}={legacy_list} → {result}")
                return result
            elif legacy_key.endswith("_disabled") or "disabled" in legacy_key:
                # Blacklist behavior: excluded items are not processed
                result = item_name not in legacy_list
                logger.debug(f"Item {item_name}: Using legacy {legacy_key}={legacy_list} → {result}")
                return result
    
    # 3. Default behavior
    result = default_behavior == "include"
    logger.debug(f"Item {item_name}: Using default ({default_behavior} all) → {result}")
    return result


def should_process_tool(tool_name: str, config: Config) -> bool:
    """Determine if a tool should be processed based on filtering configuration.

    Implements tool filtering logic with the following precedence:
    1. Individual tool controls (DISCORD_TOOL_*) - highest priority
    2. Legacy disabled_tools list (DISCORD_DISABLED_TOOLS)
    3. Default: process all tools

    Args:
        tool_name: The tool name to check (e.g., "Read", "Edit", "TodoWrite")
        config: Configuration containing filtering settings

    Returns:
        bool: True if the tool should be processed, False otherwise

    Examples:
        >>> # Individual controls take highest priority
        >>> config = {"tool_read": True, "disabled_tools": ["Read"]}
        >>> should_process_tool("Read", config)
        True
        >>>
        >>> # Legacy settings used when individual controls not set
        >>> config = {"disabled_tools": ["Read", "Edit"]}
        >>> should_process_tool("Read", config)
        False
        >>> should_process_tool("Bash", config)
        True
    """
    tool_mappings = {
        "Read": ("tool_read", "DISCORD_TOOL_READ"),
        "Edit": ("tool_edit", "DISCORD_TOOL_EDIT"),
        "MultiEdit": ("tool_multiedit", "DISCORD_TOOL_MULTIEDIT"),
        "TodoWrite": ("tool_todowrite", "DISCORD_TOOL_TODOWRITE"),
        "Grep": ("tool_grep", "DISCORD_TOOL_GREP"),
        "Glob": ("tool_glob", "DISCORD_TOOL_GLOB"),
        "LS": ("tool_ls", "DISCORD_TOOL_LS"),
        "Bash": ("tool_bash", "DISCORD_TOOL_BASH"),
        "Task": ("tool_task", "DISCORD_TOOL_TASK"),
        "WebFetch": ("tool_webfetch", "DISCORD_TOOL_WEBFETCH"),
    }
    
    return _should_process_item(
        item_name=tool_name,
        config=config,
        individual_mappings=tool_mappings,
        legacy_config_keys=("disabled_tools",),
        default_behavior="include"
    )


def should_process_event(event_type: str, config: Config) -> bool:
    """Determine if an event should be processed based on filtering configuration.

    Implements event filtering logic with the following precedence:
    1. Individual event controls (DISCORD_EVENT_*) - highest priority
    2. Legacy enabled_events list (DISCORD_ENABLED_EVENTS)
    3. Legacy disabled_events list (DISCORD_DISABLED_EVENTS)
    4. Default: process all events

    Args:
        event_type: The event type to check (e.g., "Stop", "Notification") 
        config: Configuration containing filtering settings

    Returns:
        bool: True if the event should be processed, False otherwise

    Examples:
        >>> # Individual controls take highest priority
        >>> config = {"event_stop": False, "enabled_events": ["Stop"]}
        >>> should_process_event("Stop", config)
        False
        >>>
        >>> # Legacy settings used when individual controls not set
        >>> config = {"enabled_events": ["Stop", "Notification"], "disabled_events": None}
        >>> should_process_event("Stop", config)
        True
        >>> should_process_event("PreToolUse", config)
        False
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # 1. Check individual event controls first (highest priority)
    individual_setting = None
    individual_key = None
    if event_type == "PreToolUse":
        individual_setting = config.get("event_pretooluse")
        individual_key = "DISCORD_EVENT_PRETOOLUSE"
    elif event_type == "PostToolUse":
        individual_setting = config.get("event_posttooluse")
        individual_key = "DISCORD_EVENT_POSTTOOLUSE"
    elif event_type == "Notification":
        individual_setting = config.get("event_notification")
        individual_key = "DISCORD_EVENT_NOTIFICATION"
    elif event_type == "Stop":
        individual_setting = config.get("event_stop")
        individual_key = "DISCORD_EVENT_STOP"
    elif event_type == "SubagentStop":
        individual_setting = config.get("event_subagent_stop")
        individual_key = "DISCORD_EVENT_SUBAGENT_STOP"
    
    # If individual setting is explicitly set, use it
    if individual_setting is not None:
        result = individual_setting
        logger.debug(f"Event {event_type}: Using individual control {individual_key}={individual_setting} → {result}")
        return result

    # 2. Fall back to legacy filtering logic
    enabled_events = config.get("enabled_events")
    disabled_events = config.get("disabled_events")

    # If enabled_events is configured, only process events in that list
    if enabled_events:
        result = event_type in enabled_events
        logger.debug(f"Event {event_type}: Using legacy DISCORD_ENABLED_EVENTS={enabled_events} → {result}")
        return result

    # If disabled_events is configured, skip events in that list
    if disabled_events:
        result = event_type not in disabled_events
        logger.debug(f"Event {event_type}: Using legacy DISCORD_DISABLED_EVENTS={disabled_events} → {result}")
        return result

    # 3. Default: process all events
    logger.debug(f"Event {event_type}: Using default (all events enabled) → True")
    return True


class ConfigLoader:
    """Configuration loader with validation."""

    @staticmethod
    def merge_config(base: Config, overrides: dict[str, object]) -> Config:
        """Merge configurations immutably using copy.replace().

        Args:
            base: Base configuration to start from
            overrides: Dictionary of values to override

        Returns:
            New configuration with overrides applied
        """
        # Create a new config dict with base values and apply valid overrides
        new_config = dict(base)
        new_config.update({key: value for key, value in overrides.items() if value is not None and key in base})

        return cast("Config", new_config)

    @staticmethod
    def _get_default_config() -> Config:
        """Get default configuration."""
        return {
            "bot_token": None,
            "channel_id": None,
            "debug": False,
            "use_threads": False,
            "channel_type": "text",
            "thread_prefix": DEFAULT_THREAD_PREFIX,
            "thread_storage_path": None,
            "thread_cleanup_days": DEFAULT_THREAD_CLEANUP_DAYS,
            "mention_user_id": None,
            "enabled_events": None,
            "disabled_events": None,
            "disabled_tools": None,
        }

    @staticmethod
    def _apply_env_file(config: Config, env_vars: dict[str, str]) -> Config:
        """Apply configuration from environment file immutably."""
        updates: dict[str, object] = {}

        # Simple string assignments
        simple_mappings = {
            ENV_BOT_TOKEN: "bot_token",
            ENV_CHANNEL_ID: "channel_id",
            ENV_THREAD_PREFIX: "thread_prefix",
            ENV_MENTION_USER_ID: "mention_user_id",
            ENV_THREAD_STORAGE_PATH: "thread_storage_path",
        }

        for env_key, config_key in simple_mappings.items():
            if env_key in env_vars:
                updates[config_key] = env_vars[env_key]

        # Boolean flags
        if ENV_DEBUG in env_vars:
            updates["debug"] = env_vars[ENV_DEBUG] == "1"
        if ENV_USE_THREADS in env_vars:
            updates["use_threads"] = env_vars[ENV_USE_THREADS] == "1"

        # Special handling
        if ENV_CHANNEL_TYPE in env_vars:
            channel_type = env_vars[ENV_CHANNEL_TYPE]
            if channel_type in ["text", "forum"]:
                updates["channel_type"] = cast("Literal['text', 'forum']", channel_type)

        if ENV_ENABLED_EVENTS in env_vars:
            enabled_events = parse_event_list(env_vars[ENV_ENABLED_EVENTS])
            updates["enabled_events"] = enabled_events if enabled_events else None

        if ENV_DISABLED_EVENTS in env_vars:
            disabled_events = parse_event_list(env_vars[ENV_DISABLED_EVENTS])
            updates["disabled_events"] = disabled_events if disabled_events else None

        if ENV_DISABLED_TOOLS in env_vars:
            disabled_tools = parse_tool_list(env_vars[ENV_DISABLED_TOOLS])
            updates["disabled_tools"] = disabled_tools if disabled_tools else None

        # Individual event controls (recommended)
        if ENV_EVENT_PRETOOLUSE in env_vars:
            updates["event_pretooluse"] = parse_bool_env(env_vars[ENV_EVENT_PRETOOLUSE])
        if ENV_EVENT_POSTTOOLUSE in env_vars:
            updates["event_posttooluse"] = parse_bool_env(env_vars[ENV_EVENT_POSTTOOLUSE])
        if ENV_EVENT_NOTIFICATION in env_vars:
            updates["event_notification"] = parse_bool_env(env_vars[ENV_EVENT_NOTIFICATION])
        if ENV_EVENT_STOP in env_vars:
            updates["event_stop"] = parse_bool_env(env_vars[ENV_EVENT_STOP])
        if ENV_EVENT_SUBAGENT_STOP in env_vars:
            updates["event_subagent_stop"] = parse_bool_env(env_vars[ENV_EVENT_SUBAGENT_STOP])

        # Individual tool controls (recommended)
        if ENV_TOOL_READ in env_vars:
            updates["tool_read"] = parse_bool_env(env_vars[ENV_TOOL_READ])
        if ENV_TOOL_EDIT in env_vars:
            updates["tool_edit"] = parse_bool_env(env_vars[ENV_TOOL_EDIT])
        if ENV_TOOL_MULTIEDIT in env_vars:
            updates["tool_multiedit"] = parse_bool_env(env_vars[ENV_TOOL_MULTIEDIT])
        if ENV_TOOL_TODOWRITE in env_vars:
            updates["tool_todowrite"] = parse_bool_env(env_vars[ENV_TOOL_TODOWRITE])
        if ENV_TOOL_GREP in env_vars:
            updates["tool_grep"] = parse_bool_env(env_vars[ENV_TOOL_GREP])
        if ENV_TOOL_GLOB in env_vars:
            updates["tool_glob"] = parse_bool_env(env_vars[ENV_TOOL_GLOB])
        if ENV_TOOL_LS in env_vars:
            updates["tool_ls"] = parse_bool_env(env_vars[ENV_TOOL_LS])
        if ENV_TOOL_BASH in env_vars:
            updates["tool_bash"] = parse_bool_env(env_vars[ENV_TOOL_BASH])
        if ENV_TOOL_TASK in env_vars:
            updates["tool_task"] = parse_bool_env(env_vars[ENV_TOOL_TASK])
        if ENV_TOOL_WEBFETCH in env_vars:
            updates["tool_webfetch"] = parse_bool_env(env_vars[ENV_TOOL_WEBFETCH])

        if ENV_THREAD_CLEANUP_DAYS in env_vars:
            try:
                cleanup_days = int(env_vars[ENV_THREAD_CLEANUP_DAYS])
                if cleanup_days > 0:
                    updates["thread_cleanup_days"] = cleanup_days
            except ValueError:
                pass  # Keep default value if invalid

        # Return new config with updates applied
        if updates:
            new_config = dict(config)
            new_config.update(updates)
            return cast("Config", new_config)
        return config

    @staticmethod
    def _apply_env_vars(config: Config) -> Config:
        """Apply configuration from environment variables immutably."""
        updates: dict[str, object] = {}

        # Simple string assignments
        simple_mappings = {
            ENV_BOT_TOKEN: "bot_token",
            ENV_CHANNEL_ID: "channel_id",
            ENV_MENTION_USER_ID: "mention_user_id",
            ENV_THREAD_STORAGE_PATH: "thread_storage_path",
        }

        for env_key, config_key in simple_mappings.items():
            value = os.environ.get(env_key)
            if value:
                updates[config_key] = value

        # Boolean flags
        if os.environ.get(ENV_DEBUG):
            updates["debug"] = os.environ.get(ENV_DEBUG) == "1"
        if os.environ.get(ENV_USE_THREADS):
            updates["use_threads"] = os.environ.get(ENV_USE_THREADS) == "1"

        # Special handling
        env_channel_type = os.environ.get(ENV_CHANNEL_TYPE)
        if env_channel_type and env_channel_type in ["text", "forum"]:
            updates["channel_type"] = cast("Literal['text', 'forum']", env_channel_type)

        thread_prefix = os.environ.get(ENV_THREAD_PREFIX)
        if thread_prefix:
            updates["thread_prefix"] = thread_prefix

        if os.environ.get(ENV_ENABLED_EVENTS):
            enabled_events = parse_event_list(os.environ.get(ENV_ENABLED_EVENTS, ""))
            updates["enabled_events"] = enabled_events if enabled_events else None

        if os.environ.get(ENV_DISABLED_EVENTS):
            disabled_events = parse_event_list(os.environ.get(ENV_DISABLED_EVENTS, ""))
            updates["disabled_events"] = disabled_events if disabled_events else None

        if os.environ.get(ENV_DISABLED_TOOLS):
            disabled_tools = parse_tool_list(os.environ.get(ENV_DISABLED_TOOLS, ""))
            updates["disabled_tools"] = disabled_tools if disabled_tools else None

        # Individual event controls (recommended)
        if os.environ.get(ENV_EVENT_PRETOOLUSE):
            updates["event_pretooluse"] = parse_bool_env(os.environ.get(ENV_EVENT_PRETOOLUSE))
        if os.environ.get(ENV_EVENT_POSTTOOLUSE):
            updates["event_posttooluse"] = parse_bool_env(os.environ.get(ENV_EVENT_POSTTOOLUSE))
        if os.environ.get(ENV_EVENT_NOTIFICATION):
            updates["event_notification"] = parse_bool_env(os.environ.get(ENV_EVENT_NOTIFICATION))
        if os.environ.get(ENV_EVENT_STOP):
            updates["event_stop"] = parse_bool_env(os.environ.get(ENV_EVENT_STOP))
        if os.environ.get(ENV_EVENT_SUBAGENT_STOP):
            updates["event_subagent_stop"] = parse_bool_env(os.environ.get(ENV_EVENT_SUBAGENT_STOP))

        # Individual tool controls (recommended)
        if os.environ.get(ENV_TOOL_READ):
            updates["tool_read"] = parse_bool_env(os.environ.get(ENV_TOOL_READ))
        if os.environ.get(ENV_TOOL_EDIT):
            updates["tool_edit"] = parse_bool_env(os.environ.get(ENV_TOOL_EDIT))
        if os.environ.get(ENV_TOOL_MULTIEDIT):
            updates["tool_multiedit"] = parse_bool_env(os.environ.get(ENV_TOOL_MULTIEDIT))
        if os.environ.get(ENV_TOOL_TODOWRITE):
            updates["tool_todowrite"] = parse_bool_env(os.environ.get(ENV_TOOL_TODOWRITE))
        if os.environ.get(ENV_TOOL_GREP):
            updates["tool_grep"] = parse_bool_env(os.environ.get(ENV_TOOL_GREP))
        if os.environ.get(ENV_TOOL_GLOB):
            updates["tool_glob"] = parse_bool_env(os.environ.get(ENV_TOOL_GLOB))
        if os.environ.get(ENV_TOOL_LS):
            updates["tool_ls"] = parse_bool_env(os.environ.get(ENV_TOOL_LS))
        if os.environ.get(ENV_TOOL_BASH):
            updates["tool_bash"] = parse_bool_env(os.environ.get(ENV_TOOL_BASH))
        if os.environ.get(ENV_TOOL_TASK):
            updates["tool_task"] = parse_bool_env(os.environ.get(ENV_TOOL_TASK))
        if os.environ.get(ENV_TOOL_WEBFETCH):
            updates["tool_webfetch"] = parse_bool_env(os.environ.get(ENV_TOOL_WEBFETCH))

        if os.environ.get(ENV_THREAD_CLEANUP_DAYS):
            try:
                cleanup_days = int(os.environ.get(ENV_THREAD_CLEANUP_DAYS, str(DEFAULT_THREAD_CLEANUP_DAYS)))
                if cleanup_days > 0:
                    updates["thread_cleanup_days"] = cleanup_days
            except ValueError:
                pass  # Keep default value if invalid

        # Return new config with updates applied
        if updates:
            new_config = dict(config)
            new_config.update(updates)
            return cast("Config", new_config)
        return config

    @staticmethod
    def load() -> Config:
        """Load Discord configuration with clear precedence: env vars override file config."""
        # 1. Start with defaults
        config = ConfigLoader._get_default_config()

        # 2. Load from single standard configuration file
        config_file = Path.home() / ".claude" / ".env"
        
        if config_file.exists():
            try:
                env_vars = parse_env_file(config_file)
                config = ConfigLoader._apply_env_file(config, env_vars)
            except ConfigurationError:
                # If .env file parsing fails, continue with defaults
                # This ensures we don't block Claude Code
                pass

        # 3. Environment variables override file config
        return ConfigLoader._apply_env_vars(config)

    @staticmethod
    def validate(config: Config) -> None:
        """Validate configuration."""
        if not (config["bot_token"] and config["channel_id"]):
            raise ConfigurationError("Discord bot token and channel ID are required.")


def setup_logging(debug: bool) -> logging.Logger:
    """Set up logging with optional debug mode.

    Args:
        debug: Whether to enable debug logging

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(__name__)

    if debug:
        log_dir = Path.home() / ".claude" / "hooks" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"discord_notifier_{datetime.now(UTC).strftime('%Y-%m-%d')}.log"

        logging.basicConfig(
            level=logging.DEBUG,
            format=LOG_FORMAT,
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


class ConfigValidator:
    """Validator for Config TypedDict.

    Provides static methods to validate different aspects of the Discord
    configuration. Used to ensure configuration consistency and completeness
    before attempting to send messages.

    Validation Areas:
        - Credentials: Bot token/channel ID combination
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

        Checks that bot token/channel ID combination
        is available for Discord API access.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if valid credentials are configured, False otherwise

        Validation Logic:
            - Bot token + channel ID combination is required for bot API

        Example:
            >>> config = {"bot_token": "token", "channel_id": "123"}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token"}  # Missing channel_id
            >>> ConfigValidator.validate_credentials(config)  # False
        """
        return bool(config.get("bot_token") and config.get("channel_id"))

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
            - Only text channels are supported (forum channels require webhooks)
            - Text channels require bot token + channel ID for thread creation

        Thread Types:
            - Text channels: Use bot API to create public threads

        Example:
            >>> # Valid text channel config
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "text",
            ...     "bot_token": "token",
            ...     "channel_id": "123"
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # True

            >>> # Invalid: forum channel not supported
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum"
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # False
        """
        if not config.get("use_threads", False):
            return True

        channel_type = cast("str", config.get("channel_type", "text"))
        if channel_type == "forum":
            return False  # Forum channels not supported without webhooks
        if channel_type == "text":
            return bool(config.get("bot_token") and config.get("channel_id"))
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

        Validation Checks:
            1. Credentials validation (bot token/channel)
            2. Thread configuration consistency
            3. Mention user ID format validation

        Example:
            >>> config = ConfigLoader.load()
            >>> if ConfigValidator.validate_all(config):
            ...     # Configuration is valid, proceed
            ...     pass
            >>> else:
            ...     raise ConfigurationError("Invalid configuration")
        """
        return (
            ConfigValidator.validate_credentials(config)
            and ConfigValidator.validate_thread_config(config)
            and ConfigValidator.validate_mention_config(config)
        )


class ConfigFileMetadata(TypedDict):
    """Metadata for configuration file tracking."""

    file_path: str
    last_modified: float
    file_hash: str
    size: int


class ConfigFileWatcher:
    """Configuration file change detection and hot reload system.

    This class addresses Claude Code's limitation where hook settings are
    captured at startup and don't automatically reflect changes made during
    a session. It provides hot reload functionality by detecting changes to
    configuration files and allowing immediate reloading.

    Key Features:
    - File modification time tracking
    - SHA-256 hash-based change detection
    - Atomic configuration reloading
    - Enhanced validation and fallback mechanisms
    - Configuration backup and restore capabilities
    - Detailed error reporting and recovery

    Usage:
        >>> watcher = ConfigFileWatcher()
        >>> if watcher.has_config_changed():
        ...     new_config = watcher.reload_config()
    """

    _instance = None
    _config_metadata: dict[str, ConfigFileMetadata] = {}
    _last_config: Config | None = None
    _backup_config: Config | None = None
    _notification_callback = None
    _validation_errors: list[str] = []

    def __new__(cls):
        """Singleton pattern for global config watching."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hexadecimal SHA-256 hash string

        Raises:
            FileNotFoundError: If file doesn't exist
            OSError: If file cannot be read
        """
        sha256_hash = hashlib.sha256()
        try:
            with file_path.open("rb") as f:
                # Read file in chunks for memory efficiency
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
        except OSError as e:
            raise ConfigurationError(f"Cannot read config file {file_path}: {e}") from e

        return sha256_hash.hexdigest()

    @staticmethod
    def _get_file_metadata(file_path: Path) -> ConfigFileMetadata:
        """Get file metadata for change detection.

        Args:
            file_path: Path to the configuration file

        Returns:
            ConfigFileMetadata with current file information

        Raises:
            ConfigurationError: If file cannot be accessed
        """
        try:
            stat = file_path.stat()
            file_hash = ConfigFileWatcher._calculate_file_hash(file_path)

            return ConfigFileMetadata(
                file_path=str(file_path), last_modified=stat.st_mtime, file_hash=file_hash, size=stat.st_size
            )
        except OSError as e:
            raise ConfigurationError(f"Cannot access config file {file_path}: {e}") from e

    def track_config_file(self, file_path: Path) -> None:
        """Start tracking a configuration file for changes.

        Args:
            file_path: Path to the configuration file to track
        """
        if file_path.exists():
            key = str(file_path)
            try:
                self._config_metadata[key] = self._get_file_metadata(file_path)
            except ConfigurationError:
                # If we can't read the file, don't track it
                pass

    def has_config_changed(self) -> bool:
        """Check if any tracked configuration files have changed.

        Returns:
            True if any configuration file has been modified
        """
        try:
            for key, old_metadata in self._config_metadata.items():
                file_path = Path(key)

                if not file_path.exists():
                    # File was deleted - this counts as a change
                    return True

                try:
                    current_metadata = self._get_file_metadata(file_path)

                    # Check multiple change indicators for reliability
                    if (
                        current_metadata["last_modified"] != old_metadata["last_modified"]
                        or current_metadata["file_hash"] != old_metadata["file_hash"]
                        or current_metadata["size"] != old_metadata["size"]
                    ):
                        return True

                except ConfigurationError:
                    # If we can't read the file anymore, consider it changed
                    return True

        except Exception:
            # If there's any error during change detection, assume no change
            # This ensures we don't break the main application flow
            pass

        return False

    def update_tracked_files(self) -> None:
        """Update metadata for all tracked files."""
        for key in list(self._config_metadata.keys()):
            file_path = Path(key)
            if file_path.exists():
                try:
                    self._config_metadata[key] = self._get_file_metadata(file_path)
                except ConfigurationError:
                    # Remove from tracking if we can't read it
                    del self._config_metadata[key]
            else:
                # Remove deleted files from tracking
                del self._config_metadata[key]

    def validate_config_integrity(self, config: Config) -> tuple[bool, list[str]]:
        """Comprehensive validation of configuration integrity.

        Performs extensive validation beyond basic credential checks to ensure
        the configuration is not only present but also logically consistent
        and safe to use.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors: list[str] = []

        # Reset validation errors
        self._validation_errors = []

        # 1. Basic credential validation
        if not ConfigValidator.validate_credentials(config):
            errors.append("Invalid or missing Discord credentials")

        # 2. Thread configuration validation
        if not ConfigValidator.validate_thread_config(config):
            errors.append("Invalid thread configuration")

        # 3. Mention configuration validation
        if not ConfigValidator.validate_mention_config(config):
            errors.append("Invalid user mention configuration")

        # 4. Event filtering validation
        enabled_events = config.get("enabled_events")
        disabled_events = config.get("disabled_events")

        if enabled_events and disabled_events:
            overlap = set(enabled_events) & set(disabled_events)
            if overlap:
                errors.append(f"Events cannot be both enabled and disabled: {overlap}")

        # 5. Tool filtering validation
        disabled_tools = config.get("disabled_tools")
        if disabled_tools:
            # Validate tool names are reasonable (basic sanity check)
            invalid_tools = [tool for tool in disabled_tools if not tool.isalnum()]
            if invalid_tools:
                errors.append(f"Invalid tool names detected: {invalid_tools}")

        # 6. Thread configuration consistency
        if config.get("use_threads"):
            if config.get("channel_type") == "forum":
                errors.append("Forum channels are not supported (require webhooks)")
            elif config.get("channel_type") == "text" and not (config.get("bot_token") and config.get("channel_id")):
                errors.append("Text channel threads require bot token and channel ID")

        # 7. Cleanup days validation
        cleanup_days = config.get("thread_cleanup_days", DEFAULT_THREAD_CLEANUP_DAYS)
        if cleanup_days <= 0:
            errors.append(f"Invalid thread cleanup days: {cleanup_days} (must be positive)")

        # Store validation errors for reporting
        self._validation_errors = errors

        return len(errors) == 0, errors

    def create_config_backup(self, config: Config) -> None:
        """Create a backup of known good configuration.

        Args:
            config: Configuration to backup
        """
        # Only backup if configuration passes validation
        is_valid, errors = self.validate_config_integrity(config)
        if is_valid:
            # Create a deep copy for backup
            self._backup_config = dict(config)

    def restore_from_backup(self) -> Config | None:
        """Restore configuration from backup.

        Returns:
            Backup configuration if available, None otherwise
        """
        if self._backup_config:
            # Validate backup before returning
            backup_config = cast("Config", self._backup_config)
            is_valid, _ = self.validate_config_integrity(backup_config)
            if is_valid:
                return backup_config

        return None

    def get_validation_report(self) -> str:
        """Get detailed validation error report.

        Returns:
            Formatted string with validation errors
        """
        if not self._validation_errors:
            return "✅ Configuration validation passed"

        report = "❌ Configuration validation failed:\n"
        for i, error in enumerate(self._validation_errors, 1):
            report += f"  {i}. {error}\n"

        return report.strip()

    def reload_config(self) -> Config:
        """Reload configuration from files with enhanced validation and fallback.

        Returns:
            Newly loaded configuration

        Raises:
            ConfigurationError: If config loading fails and no fallback available
        """
        try:
            # Load fresh configuration
            new_config = ConfigLoader.load()

            # Comprehensive validation of new configuration
            is_valid, validation_errors = self.validate_config_integrity(new_config)

            if is_valid:
                # Configuration is valid - proceed with update
                self.update_tracked_files()

                # Create backup of previous good config before updating
                if self._last_config is not None:
                    self.create_config_backup(self._last_config)

                # Store as last known good configuration
                self._last_config = new_config

                return new_config
            else:
                # New configuration failed validation - attempt fallback
                validation_report = self.get_validation_report()

                # Try to restore from backup first
                backup_config = self.restore_from_backup()
                if backup_config is not None:
                    error_msg = f"New config validation failed, restored from backup.\n{validation_report}"
                    raise ConfigurationError(error_msg)

                # Try previous config as fallback
                if self._last_config is not None:
                    error_msg = f"New config validation failed, using previous config.\n{validation_report}"
                    raise ConfigurationError(error_msg)

                # No valid fallback available - this is a critical error
                error_msg = f"Config validation failed and no valid fallback available.\n{validation_report}"
                raise ConfigurationError(error_msg)

        except ConfigurationError:
            # Re-raise configuration errors as-is (they include our enhanced error messages)
            raise

        except Exception as e:
            # Handle unexpected errors during loading

            # Try to restore from backup first
            backup_config = self.restore_from_backup()
            if backup_config is not None:
                self._last_config = backup_config
                raise ConfigurationError(f"Config reload failed unexpectedly, restored from backup: {e}") from e

            # Try previous config as fallback
            if self._last_config is not None:
                raise ConfigurationError(f"Config reload failed unexpectedly, using previous configuration: {e}") from e

            # No fallback available - critical failure
            raise ConfigurationError(f"Config reload failed with no fallback available: {e}") from e

    def get_config_with_auto_reload(self) -> Config:
        """Get configuration with automatic reload if files changed.

        This is the main method for getting configuration that automatically
        detects and applies changes without requiring Claude Code restart.

        Returns:
            Current configuration (potentially reloaded)
        """
        # Set up tracking for standard config file on first call
        if not self._config_metadata:
            self.track_config_file(Path("~/.claude/.env").expanduser())

        # Check if any config files have changed
        if self.has_config_changed():
            try:
                return self.reload_config()
            except ConfigurationError:
                # If reload fails, fall back to normal config loading
                if self._last_config is not None:
                    return self._last_config
                return ConfigLoader.load()

        # No changes detected, use cached config or load normally
        if self._last_config is not None:
            return self._last_config

        # First time loading
        config = ConfigLoader.load()
        self._last_config = config
        return config

    def set_notification_callback(self, callback) -> None:
        """Set callback function for configuration change notifications.

        Args:
            callback: Function to call when config changes are detected.
                     Should accept (message: str, is_error: bool) parameters.
        """
        self._notification_callback = callback

    def _send_config_change_notification(self, message: str, is_error: bool = False) -> None:
        """Send configuration change notification via callback.

        Args:
            message: Notification message to send
            is_error: Whether this is an error notification
        """
        if self._notification_callback:
            try:
                self._notification_callback(message, is_error)
            except Exception:
                # Don't let notification failures break the main flow
                pass

    def get_config_with_auto_reload_and_notify(self) -> Config:
        """Get configuration with auto-reload, validation, and change notifications.

        Enhanced version with comprehensive validation, backup/restore capabilities,
        and detailed error reporting via Discord notifications.

        Returns:
            Current configuration (potentially reloaded)
        """
        # Set up tracking for standard config file on first call
        if not self._config_metadata:
            self.track_config_file(Path("~/.claude/.env").expanduser())

        # Check if any config files have changed
        if self.has_config_changed():
            try:
                new_config = self.reload_config()

                # Send success notification with validation status
                changed_files = []
                for key in self._config_metadata.keys():
                    file_path = Path(key)
                    if file_path.exists():
                        changed_files.append(file_path.name)

                files_text = ", ".join(changed_files) if changed_files else "config files"
                validation_report = self.get_validation_report()

                if validation_report.startswith("✅"):
                    message = f"🔄 Configuration reloaded: {files_text} updated.\n{validation_report}\nNew settings applied immediately!"
                else:
                    message = f"🔄 Configuration reloaded: {files_text} updated.\n{validation_report}"

                self._send_config_change_notification(message, is_error=False)

                return new_config

            except ConfigurationError as e:
                # Enhanced error notification with validation details
                error_str = str(e)

                # Check if we're using a fallback
                if "backup" in error_str.lower():
                    message = f"🔄 Configuration restored from backup:\n{error_str}"
                    self._send_config_change_notification(message, is_error=False)
                elif "previous" in error_str.lower():
                    message = f"⚠️ Configuration error - using previous settings:\n{error_str}"
                    self._send_config_change_notification(message, is_error=True)
                else:
                    message = f"🚨 Critical configuration error:\n{error_str}"
                    self._send_config_change_notification(message, is_error=True)

                # Determine best fallback strategy
                backup_config = self.restore_from_backup()
                if backup_config is not None:
                    self._last_config = backup_config
                    return backup_config

                if self._last_config is not None:
                    return self._last_config

                # Last resort - load default config
                return ConfigLoader.load()

        # No changes detected, use cached config or load normally
        if self._last_config is not None:
            return self._last_config

        # First time loading with enhanced validation
        config = ConfigLoader.load()

        # Validate initial configuration
        is_valid, validation_errors = self.validate_config_integrity(config)

        if is_valid:
            self._last_config = config
            self.create_config_backup(config)  # Create initial backup

            # NOTE: Removed initialization notification to prevent spam on every hook execution
            # Only send notifications when configuration actually changes, not on first load
        else:
            # Initial config is invalid - proceed without notification to prevent spam
            # Only send notifications when configuration actually changes, not on first load

            # Still store it as last config for fallback purposes
            self._last_config = config

        return config
