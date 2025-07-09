#!/usr/bin/env python3
"""Configuration management for Discord Notifier.

This module handles loading and validation of configuration from
environment variables and .env files.
"""

import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# Python 3.13+ features
from typing import Literal, TypedDict, cast

# ReadOnly - use typing_extensions for compatibility
try:
    from typing import ReadOnly
except ImportError:
    from typing import ReadOnly

from .constants import (
    DEFAULT_THREAD_CLEANUP_DAYS,
    DEFAULT_THREAD_PREFIX,
    ENV_BOT_TOKEN,
    ENV_CHANNEL_ID,
    ENV_CHANNEL_TYPE,
    ENV_DEBUG,
    ENV_DISABLED_EVENTS,
    ENV_ENABLED_EVENTS,
    ENV_MENTION_USER_ID,
    ENV_THREAD_CLEANUP_DAYS,
    ENV_THREAD_PREFIX,
    ENV_THREAD_STORAGE_PATH,
    ENV_USE_THREADS,
    ENV_WEBHOOK_URL,
    LOG_FORMAT,
    EventTypes,
)
from .exceptions import ConfigurationError


# Configuration TypedDict hierarchy
class DiscordCredentials(TypedDict):
    """Discord authentication credentials."""

    webhook_url: ReadOnly[str | None]
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


class EventFilterConfiguration(TypedDict):
    """Event filtering configuration."""

    enabled_events: list[str] | None
    disabled_events: list[str] | None


class Config(
    DiscordCredentials,
    ThreadConfiguration,
    NotificationConfiguration,
    EventFilterConfiguration,
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
        DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123/abc
        DISCORD_TOKEN="your_bot_token_here"
        DISCORD_CHANNEL_ID='123456789012345678'
        # Thread settings
        DISCORD_USE_THREADS=1
        ```

    Example Usage:
        >>> env_vars = parse_env_file(Path(".env.discord"))
        >>> webhook_url = env_vars.get("DISCORD_WEBHOOK_URL")

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


def should_process_event(event_type: str, config: Config) -> bool:
    """Determine if an event should be processed based on filtering configuration.

    Implements event filtering logic with the following precedence:
    1. If enabled_events is configured, only process events in that list
    2. If disabled_events is configured, skip events in that list
    3. If both are configured, enabled_events takes precedence
    4. If neither is configured, process all events (default behavior)

    Args:
        event_type: The event type to check (e.g., "Stop", "Notification")
        config: Configuration containing filtering settings

    Returns:
        bool: True if the event should be processed, False otherwise

    Examples:
        >>> config = {"enabled_events": ["Stop", "Notification"], "disabled_events": None}
        >>> should_process_event("Stop", config)
        True
        >>> should_process_event("PreToolUse", config)
        False
        >>>
        >>> config = {"enabled_events": None, "disabled_events": ["PreToolUse"]}
        >>> should_process_event("PreToolUse", config)
        False
        >>> should_process_event("Stop", config)
        True
    """
    enabled_events = config.get("enabled_events")
    disabled_events = config.get("disabled_events")

    # If enabled_events is configured, only process events in that list
    if enabled_events:
        return event_type in enabled_events

    # If disabled_events is configured, skip events in that list
    if disabled_events:
        return event_type not in disabled_events

    # Default: process all events
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
            "webhook_url": None,
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
        }

    @staticmethod
    def _apply_env_file(config: Config, env_vars: dict[str, str]) -> Config:
        """Apply configuration from environment file immutably."""
        updates: dict[str, object] = {}

        # Simple string assignments
        simple_mappings = {
            ENV_WEBHOOK_URL: "webhook_url",
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
            ENV_WEBHOOK_URL: "webhook_url",
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

        # 2. Load from .env file if it exists in project root
        env_file = Path(".env")
        if env_file.exists():
            try:
                env_vars = parse_env_file(env_file)
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
        if not config["webhook_url"] and not (config["bot_token"] and config["channel_id"]):
            raise ConfigurationError("No Discord configuration found. Please set webhook URL or bot token/channel ID.")


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
        - Credentials: Webhook URL or bot token/channel ID combination
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

        Checks that either webhook URL or bot token/channel ID combination
        is available for Discord API access.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if valid credentials are configured, False otherwise

        Validation Logic:
            - Webhook URL alone is sufficient for basic messaging
            - Bot token + channel ID combination is required for bot API
            - At least one method must be configured

        Example:
            >>> config = {"webhook_url": "https://discord.com/api/webhooks/..."}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token", "channel_id": "123"}
            >>> ConfigValidator.validate_credentials(config)  # True
            >>> config = {"bot_token": "token"}  # Missing channel_id
            >>> ConfigValidator.validate_credentials(config)  # False
        """
        return bool(config.get("webhook_url") or (config.get("bot_token") and config.get("channel_id")))

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
            - Forum channels require webhook URL for thread creation
            - Text channels require bot token + channel ID for thread creation
            - Invalid channel types are rejected

        Thread Types:
            - Forum channels: Use webhook API with thread_name parameter
            - Text channels: Use bot API to create public threads

        Example:
            >>> # Valid forum channel config
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum",
            ...     "webhook_url": "https://discord.com/api/webhooks/..."
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # True

            >>> # Invalid: forum channel without webhook
            >>> config = {
            ...     "use_threads": True,
            ...     "channel_type": "forum",
            ...     "bot_token": "token"
            ... }
            >>> ConfigValidator.validate_thread_config(config)  # False
        """
        if not config.get("use_threads", False):
            return True

        channel_type = cast("str", config.get("channel_type", "text"))
        if channel_type == "forum":
            return bool(config.get("webhook_url"))
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
            1. Credentials validation (webhook URL or bot token/channel)
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
