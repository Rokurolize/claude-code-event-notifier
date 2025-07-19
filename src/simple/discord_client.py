#!/usr/bin/env python3
"""Simple Discord client for sending messages.

This module provides a clean interface for sending messages to Discord
via webhook or bot API.
"""

import json
import urllib.error
import urllib.request
from typing import Any

from event_types import Config, DiscordMessage

# Python 3.14+ required - pure standard library


def send_to_discord(message: DiscordMessage, config: Config) -> bool:
    """Send message to Discord.
    
    Supports both webhook and bot API methods.
    
    Args:
        message: Discord message with embeds and/or content
        config: Configuration with Discord credentials
        
    Returns:
        True if successful, False otherwise
    """
    # Try webhook first (simpler)
    if webhook_url := config.get("webhook_url"):
        return _send_via_webhook(message, webhook_url)
    
    # Fall back to bot API
    if bot_token := config.get("bot_token"):
        if channel_id := config.get("channel_id"):
            return _send_via_bot_api(message, bot_token, channel_id)
    
    return False


def _send_via_webhook(message: DiscordMessage, webhook_url: str) -> bool:
    """Send message via Discord webhook."""
    try:
        data = json.dumps(message).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 204
            
    except Exception:
        # Silently fail - don't block Claude Code
        return False


def _send_via_bot_api(message: DiscordMessage, bot_token: str, channel_id: str) -> bool:
    """Send message via Discord bot API."""
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        data = json.dumps(message).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bot {bot_token}",
                "Content-Type": "application/json",
                "User-Agent": "Discord-Event-Notifier/1.0"
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return 200 <= response.status < 300
            
    except Exception:
        # Silently fail - don't block Claude Code
        return False