"""Configuration loader for Discord Notifier.

This module handles loading and validating configuration from
environment variables and .env files.
"""

import os
import sys
from pathlib import Path
from typing import cast, Literal

# Try to import types from type_defs module first
try:
    from src.type_defs.config import Config
except ImportError:
    # Fallback imports if type_defs not available
    from discord_notifier import Config  # type: ignore

# Try to import constants
try:
    from src.constants import (
        ENV_WEBHOOK_URL, ENV_BOT_TOKEN, ENV_CHANNEL_ID, ENV_DEBUG,
        ENV_USE_THREADS, ENV_CHANNEL_TYPE, ENV_THREAD_PREFIX,
        ENV_MENTION_USER_ID, ENV_ENABLED_EVENTS, ENV_DISABLED_EVENTS,
        ENV_THREAD_STORAGE_PATH, ENV_THREAD_CLEANUP_DAYS,
    )
except ImportError:
    # Fallback imports if constants not available
    from discord_notifier import (  # type: ignore
        ENV_WEBHOOK_URL, ENV_BOT_TOKEN, ENV_CHANNEL_ID, ENV_DEBUG,
        ENV_USE_THREADS, ENV_CHANNEL_TYPE, ENV_THREAD_PREFIX,
        ENV_MENTION_USER_ID, ENV_ENABLED_EVENTS, ENV_DISABLED_EVENTS,
        ENV_THREAD_STORAGE_PATH, ENV_THREAD_CLEANUP_DAYS,
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
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"\'')
        except Exception as e:
            raise ConfigurationError(f"Failed to parse .env file: {e}")
        return env_vars
    
    def parse_event_list(event_list_str: str) -> list[str]:
        """Parse comma-separated event list."""
        if not event_list_str.strip():
            return []
        events = [e.strip() for e in event_list_str.split(',') if e.strip()]
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

    @staticmethod
    def _get_default_config() -> Config:
        """Get default configuration."""
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
        if ENV_WEBHOOK_URL in env_vars:
            value = env_vars[ENV_WEBHOOK_URL]
            config["webhook_url"] = value if value else None
        if ENV_BOT_TOKEN in env_vars:
            value = env_vars[ENV_BOT_TOKEN]
            config["bot_token"] = value if value else None
        if ENV_CHANNEL_ID in env_vars:
            value = env_vars[ENV_CHANNEL_ID]
            config["channel_id"] = value if value else None
        if ENV_DEBUG in env_vars:
            config["debug"] = env_vars[ENV_DEBUG] == "1"
        if ENV_USE_THREADS in env_vars:
            config["use_threads"] = env_vars[ENV_USE_THREADS] == "1"
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
        if ENV_DISABLED_EVENTS in env_vars:
            disabled_events = parse_event_list(env_vars[ENV_DISABLED_EVENTS])
            config["disabled_events"] = disabled_events if disabled_events else None
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
        # 1. Start with defaults
        config = ConfigLoader._get_default_config()

        # 2. Load from .env file if it exists
        env_file = Path("/home/ubuntu/claude_code_event_notifier/.env")
        if env_file.exists():
            try:
                env_vars = parse_env_file(env_file)
                ConfigLoader._update_config_from_dict(config, env_vars)
            except Exception:
                # Don't exit during tests - just skip the file
                pass

        # 3. Environment variables override file config
        ConfigLoader._update_config_from_environment(config)

        return config

    @staticmethod
    def validate(config: Config) -> None:
        """Validate configuration."""
        if not config["webhook_url"] and not (config["bot_token"] and config["channel_id"]):
            raise ConfigurationError("No Discord configuration found. Please set webhook URL or bot token/channel ID.")


# Export all public items
__all__ = ['ConfigLoader', 'DEFAULT_CONFIG']