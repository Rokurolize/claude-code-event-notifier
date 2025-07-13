"""Configuration loader for Discord Notifier.

This module handles loading and validating configuration from
environment variables and .env files.
"""

import os
from pathlib import Path
from typing import Literal, cast

# Import AstolfoLogger for structured logging
try:
    from src.utils.astolfo_logger import AstolfoLogger
except ImportError:
    # Fallback if AstolfoLogger not available
    AstolfoLogger = None  # type: ignore

# Try to import types from type_defs module first
try:
    from src.type_defs.config import Config
except ImportError:
    # Fallback imports if type_defs not available
    from discord_notifier import Config  # type: ignore

# Try to import constants
try:
    from src.constants import (
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
    )
except ImportError:
    # Fallback imports if constants not available
    from discord_notifier import (  # type: ignore
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
    )

# Try to import exceptions
try:
    from src.exceptions import ConfigurationError
except ImportError:
    # Fallback imports if exceptions not available
    from discord_notifier import ConfigurationError  # type: ignore

# Try to import utility functions
try:
    from src.utils.discord_utils import parse_env_file, parse_event_list
except ImportError:
    # Simple fallback implementations
    def parse_env_file(file_path: Path) -> dict[str, str]:
        """Parse .env file into a dictionary."""
        env_vars = {}
        try:
            with open(file_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        except Exception as e:
            raise ConfigurationError(f"Failed to parse .env file: {e}")
        return env_vars

    def parse_event_list(event_list_str: str) -> list[str]:
        """Parse comma-separated event list."""
        if not event_list_str.strip():
            return []
        events = [e.strip() for e in event_list_str.split(",") if e.strip()]
        return events if events else []


# Default configuration
DEFAULT_CONFIG: Config = {
    "webhook_url": None,
    "bot_token": None,
    "channel_id": None,
    "debug": False,
    "use_threads": False,
    "channel_type": "text",
    "thread_prefix": "Session",
    "thread_storage_path": None,
    "thread_cleanup_days": 30,
    "mention_user_id": None,
    "enabled_events": None,
    "disabled_events": None,
}


class ConfigLoader:
    """Configuration loader with validation."""

    # Initialize logger for config loading
    _logger = AstolfoLogger(name="ConfigLoader") if AstolfoLogger else None

    @staticmethod
    def _get_default_config() -> Config:
        """Get default configuration."""
        if ConfigLoader._logger:
            ConfigLoader._logger.debug("Creating default configuration")

        # Return a deep copy to avoid mutation
        return {
            "webhook_url": DEFAULT_CONFIG["webhook_url"],
            "bot_token": DEFAULT_CONFIG["bot_token"],
            "channel_id": DEFAULT_CONFIG["channel_id"],
            "debug": DEFAULT_CONFIG["debug"],
            "use_threads": DEFAULT_CONFIG["use_threads"],
            "channel_type": DEFAULT_CONFIG["channel_type"],
            "thread_prefix": DEFAULT_CONFIG["thread_prefix"],
            "thread_storage_path": DEFAULT_CONFIG["thread_storage_path"],
            "thread_cleanup_days": DEFAULT_CONFIG["thread_cleanup_days"],
            "mention_user_id": DEFAULT_CONFIG["mention_user_id"],
            "enabled_events": DEFAULT_CONFIG["enabled_events"],
            "disabled_events": DEFAULT_CONFIG["disabled_events"],
        }

    @staticmethod
    def _update_config_from_dict(config: Config, env_vars: dict[str, str]) -> None:
        """Update config from environment variable dictionary."""
        if ConfigLoader._logger:
            ConfigLoader._logger.debug(
                "Updating config from dictionary",
                {"env_vars_count": len(env_vars), "keys": list(env_vars.keys())}
            )

        if ENV_WEBHOOK_URL in env_vars:
            value = env_vars[ENV_WEBHOOK_URL]
            config["webhook_url"] = value if value else None
            if ConfigLoader._logger and value:
                ConfigLoader._logger.debug("Webhook URL configured", {"has_value": bool(value)})
        if ENV_BOT_TOKEN in env_vars:
            value = env_vars[ENV_BOT_TOKEN]
            config["bot_token"] = value if value else None
            if ConfigLoader._logger and value:
                ConfigLoader._logger.debug("Bot token configured", {"has_value": bool(value)})
        if ENV_CHANNEL_ID in env_vars:
            value = env_vars[ENV_CHANNEL_ID]
            config["channel_id"] = value if value else None
            if ConfigLoader._logger and value:
                ConfigLoader._logger.debug("Channel ID configured", {"channel_id": value})
        if ENV_DEBUG in env_vars:
            config["debug"] = env_vars[ENV_DEBUG] == "1"
            if ConfigLoader._logger:
                ConfigLoader._logger.debug("Debug mode set", {"debug": config["debug"]})
        if ENV_USE_THREADS in env_vars:
            config["use_threads"] = env_vars[ENV_USE_THREADS] == "1"
            if ConfigLoader._logger:
                ConfigLoader._logger.debug("Thread usage configured", {"use_threads": config["use_threads"]})
        if ENV_CHANNEL_TYPE in env_vars:
            channel_type = env_vars[ENV_CHANNEL_TYPE]
            if channel_type in ["text", "forum"]:
                config["channel_type"] = cast("Literal['text', 'forum']", channel_type)
        if ENV_THREAD_PREFIX in env_vars:
            value = env_vars[ENV_THREAD_PREFIX]
            config["thread_prefix"] = value if value else "Session"
        if ENV_MENTION_USER_ID in env_vars:
            value = env_vars[ENV_MENTION_USER_ID]
            config["mention_user_id"] = value if value else None
        if ENV_ENABLED_EVENTS in env_vars:
            enabled_events = parse_event_list(env_vars[ENV_ENABLED_EVENTS])
            config["enabled_events"] = enabled_events if enabled_events else None
            if ConfigLoader._logger and enabled_events:
                ConfigLoader._logger.debug(
                    "Enabled events configured",
                    {"events": enabled_events, "count": len(enabled_events)}
                )
        if ENV_DISABLED_EVENTS in env_vars:
            disabled_events = parse_event_list(env_vars[ENV_DISABLED_EVENTS])
            config["disabled_events"] = disabled_events if disabled_events else None
            if ConfigLoader._logger and disabled_events:
                ConfigLoader._logger.debug(
                    "Disabled events configured",
                    {"events": disabled_events, "count": len(disabled_events)}
                )
        if ENV_THREAD_STORAGE_PATH in env_vars:
            value = env_vars[ENV_THREAD_STORAGE_PATH]
            config["thread_storage_path"] = value if value else None
        if ENV_THREAD_CLEANUP_DAYS in env_vars:
            try:
                cleanup_days = int(env_vars[ENV_THREAD_CLEANUP_DAYS])
                if cleanup_days > 0:
                    config["thread_cleanup_days"] = cleanup_days
            except ValueError:
                pass  # Keep default value if invalid

    @staticmethod
    def _update_config_from_environment(config: Config) -> None:
        """Update config from environment variables."""
        env_dict = {}

        # Build a dictionary from environment variables
        for env_var in [
            ENV_WEBHOOK_URL,
            ENV_BOT_TOKEN,
            ENV_CHANNEL_ID,
            ENV_DEBUG,
            ENV_USE_THREADS,
            ENV_CHANNEL_TYPE,
            ENV_THREAD_PREFIX,
            ENV_MENTION_USER_ID,
            ENV_ENABLED_EVENTS,
            ENV_DISABLED_EVENTS,
            ENV_THREAD_STORAGE_PATH,
            ENV_THREAD_CLEANUP_DAYS,
        ]:
            value = os.environ.get(env_var)
            if value is not None:
                env_dict[env_var] = value

        # Use the same update logic
        ConfigLoader._update_config_from_dict(config, env_dict)

    @staticmethod
    def load() -> Config:
        """Load Discord configuration with clear precedence: env vars override file config."""
        if ConfigLoader._logger:
            ConfigLoader._logger.info("Starting configuration load")

        # 1. Start with defaults
        config = ConfigLoader._get_default_config()

        # 2. Load from .env file if it exists
        env_file = Path("/home/ubuntu/claude_code_event_notifier/.env")
        if env_file.exists():
            try:
                if ConfigLoader._logger:
                    ConfigLoader._logger.debug(f"Loading .env file from {env_file}")
                env_vars = parse_env_file(env_file)
                ConfigLoader._update_config_from_dict(config, env_vars)
                if ConfigLoader._logger:
                    ConfigLoader._logger.info(
                        "Successfully loaded .env file",
                        {"path": str(env_file), "var_count": len(env_vars)}
                    )
            except Exception as e:
                # Don't exit during tests - just skip the file
                if ConfigLoader._logger:
                    ConfigLoader._logger.warning(
                        "Failed to load .env file",
                        {"path": str(env_file), "error": str(e)}
                    )

        # 3. Environment variables override file config
        if ConfigLoader._logger:
            ConfigLoader._logger.debug("Loading from environment variables")
        ConfigLoader._update_config_from_environment(config)

        if ConfigLoader._logger:
            # Log final configuration (without sensitive values)
            sanitized_config = {
                "webhook_url": "***" if config["webhook_url"] else None,
                "bot_token": "***" if config["bot_token"] else None,
                "channel_id": config["channel_id"],
                "debug": config["debug"],
                "use_threads": config["use_threads"],
                "channel_type": config["channel_type"],
                "thread_prefix": config["thread_prefix"],
                "mention_user_id": config["mention_user_id"],
                "enabled_events": config["enabled_events"],
                "disabled_events": config["disabled_events"],
                "thread_storage_path": config["thread_storage_path"],
                "thread_cleanup_days": config["thread_cleanup_days"],
            }
            ConfigLoader._logger.info(
                "Configuration loaded successfully",
                {"config": sanitized_config}
            )

        return config

    @staticmethod
    def validate(config: Config) -> None:
        """Validate configuration."""
        if ConfigLoader._logger:
            ConfigLoader._logger.debug("Validating configuration")

        if not config["webhook_url"] and not (config["bot_token"] and config["channel_id"]):
            error_msg = "No Discord configuration found. Please set webhook URL or bot token/channel ID."
            if ConfigLoader._logger:
                ConfigLoader._logger.error(
                    "Configuration validation failed",
                    {"error": error_msg}
                )
            raise ConfigurationError(error_msg)

        if ConfigLoader._logger:
            ConfigLoader._logger.info("Configuration validation passed")


# Export all public items
__all__ = ["DEFAULT_CONFIG", "ConfigLoader"]
