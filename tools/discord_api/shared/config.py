#!/usr/bin/env python3
"""Discord API configuration utilities.

Unified configuration loading for Discord API access across all tools.
"""

import os
from pathlib import Path
from typing import Optional


def get_discord_bot_token() -> Optional[str]:
    """Get Discord bot token from environment or config.

    Checks multiple sources in order of preference:
    1. DISCORD_BOT_TOKEN environment variable
    2. ~/.claude/.env file
    3. DISCORD_TOKEN environment variable (fallback)

    Returns:
        Bot token if available, None otherwise
    """
    # Try primary environment variable first
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if token:
        return token.strip()

    # Try config file
    config_file = Path.home() / ".claude" / ".env"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DISCORD_BOT_TOKEN="):
                        token = line.split("=", 1)[1].strip().strip('"\'')
                        if token:
                            return token
        except (OSError, UnicodeDecodeError):
            pass

    # Try fallback environment variable
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        return token.strip()

    return None


def get_discord_channel_id() -> Optional[str]:
    """Get Discord channel ID from environment or config.

    Checks multiple sources in order of preference:
    1. DISCORD_CHANNEL_ID environment variable
    2. ~/.claude/.env file

    Returns:
        Channel ID if available, None otherwise
    """
    # Try environment variable first
    channel_id = os.environ.get("DISCORD_CHANNEL_ID")
    if channel_id:
        return channel_id.strip()

    # Try config file
    config_file = Path.home() / ".claude" / ".env"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DISCORD_CHANNEL_ID="):
                        channel_id = line.split("=", 1)[1].strip().strip('"\'')
                        if channel_id:
                            return channel_id
        except (OSError, UnicodeDecodeError):
            pass

    return None


def validate_discord_config() -> tuple[bool, str]:
    """Validate Discord configuration.

    Returns:
        Tuple of (is_valid, error_message)
    """
    token = get_discord_bot_token()
    if not token:
        return False, "Discord bot token not found. Set DISCORD_BOT_TOKEN environment variable or add to ~/.claude/.env"

    channel_id = get_discord_channel_id()
    if not channel_id:
        return False, "Discord channel ID not found. Set DISCORD_CHANNEL_ID environment variable or add to ~/.claude/.env"

    return True, "Configuration valid"