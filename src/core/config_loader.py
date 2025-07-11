"""Configuration loader for Discord Notifier.

This module handles loading and validating configuration from
environment variables and .env files.
"""

import os
import sys
from pathlib import Path
from typing import cast

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
    
    def parse_event_list(event_str: str) -> list[str] | None:
        """Parse comma-separated event list."""
        if not event_str.strip():
            return None
        events = [e.strip() for e in event_str.split(',') if e.strip()]
        return events if events else None


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
        return DEFAULT_CONFIG.copy()

    @staticmethod
    def _update_config_from_dict(config: Config, env_vars: dict[str, str]) -> None:
        """Update config from environment variable dictionary."""
        if ENV_WEBHOOK_URL in env_vars:
            config["webhook_url"] = env_vars[ENV_WEBHOOK_URL]
        if ENV_BOT_TOKEN in env_vars:
            config["bot_token"] = env_vars[ENV_BOT_TOKEN]
        if ENV_CHANNEL_ID in env_vars:
            config["channel_id"] = env_vars[ENV_CHANNEL_ID]
        if ENV_DEBUG in env_vars:
            config["debug"] = env_vars[ENV_DEBUG] == "1"
        if ENV_USE_THREADS in env_vars:
            config["use_threads"] = env_vars[ENV_USE_THREADS] == "1"
        if ENV_CHANNEL_TYPE in env_vars:
            channel_type = env_vars[ENV_CHANNEL_TYPE]
            if channel_type in ["text", "forum"]:
                config["channel_type"] = cast("Literal['text', 'forum']", channel_type)
        if ENV_THREAD_PREFIX in env_vars:
            config["thread_prefix"] = env_vars[ENV_THREAD_PREFIX]
        if ENV_MENTION_USER_ID in env_vars:
            config["mention_user_id"] = env_vars[ENV_MENTION_USER_ID]
        if ENV_ENABLED_EVENTS in env_vars:
            enabled_events = parse_event_list(env_vars[ENV_ENABLED_EVENTS])
            config["enabled_events"] = enabled_events if enabled_events else None
        if ENV_DISABLED_EVENTS in env_vars:
            disabled_events = parse_event_list(env_vars[ENV_DISABLED_EVENTS])
            config["disabled_events"] = disabled_events if disabled_events else None
        if ENV_THREAD_STORAGE_PATH in env_vars:
            config["thread_storage_path"] = env_vars[ENV_THREAD_STORAGE_PATH]
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

        # 2. Load from .env.discord file if it exists
        env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
        if env_file.exists():
            try:
                env_vars = parse_env_file(env_file)
                ConfigLoader._update_config_from_dict(config, env_vars)
            except ConfigurationError as e:
                print(str(e), file=sys.stderr)
                sys.exit(1)

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