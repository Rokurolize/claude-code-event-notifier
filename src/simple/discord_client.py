#!/usr/bin/env python3
"""Simple Discord client for sending messages.

This module provides a clean interface for sending messages to Discord
via webhook or bot API.
"""

import json
import logging
import re
import urllib.error
import urllib.request

from event_types import Config, DiscordMessage

# Python 3.14+ required - pure standard library

# Setup logger
logger = logging.getLogger(__name__)

def _sanitize_log_input(value: str) -> str:
    """Sanitize input for logging to prevent log injection."""
    return re.sub(r'[\n\r]', '', str(value))


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
            
    except Exception as e:
        # Log at debug level but don't block Claude Code
        logger.debug(f"Discord webhook send failed: {type(e).__name__}: {e}")
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
            
    except Exception as e:
        # Log at debug level but don't block Claude Code
        logger.debug(f"Discord bot API send failed: {type(e).__name__}: {e}")
        return False


def create_thread(channel_id: str, name: str, bot_token: str) -> str | None:
    """Create a new thread in a Discord channel.
    
    Args:
        channel_id: Parent channel ID
        name: Thread name
        bot_token: Discord bot token
        
    Returns:
        Thread ID if successful, None otherwise
    """
    logger.debug(f"create_thread called - channel_id: {_sanitize_log_input(channel_id)}, name: {_sanitize_log_input(name)}, token_length: {len(bot_token)}")
    
    try:
        url = f"https://discord.com/api/v10/channels/{channel_id}/threads"
        
        request_data = {
            "name": (name[:97] + "...") if len(name) > 100 else name,  # Discord limit is 100 chars
            "auto_archive_duration": 1440,  # 24 hours
            "type": 11  # Public thread
        }
        logger.debug(f"Thread creation request data: {request_data}")
        
        data = json.dumps(request_data).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bot {bot_token}",  # Use full token in actual request
                "Content-Type": "application/json",
                "User-Agent": "Discord-Event-Notifier/1.0"
            }
        )
        
        logger.debug(f"Sending POST request to: {_sanitize_log_input(url)}")
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.status
            logger.debug(f"Discord API response status: {status_code}")
            
            if 200 <= status_code < 300:
                response_data = response.read()
                result = json.loads(response_data)
                thread_id = result.get("id")
                logger.debug(f"Thread created successfully - ID: {_sanitize_log_input(thread_id)}, response: {result}")
                return thread_id
            else:
                logger.debug(f"Unexpected status code: {status_code}")
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Discord API HTTPError: {e.code} - {e.reason}")
        logger.error(f"Error response body: {error_body}")
        
        # Parse error details if possible
        try:
            error_json = json.loads(error_body)
            logger.error(f"Discord error message: {error_json.get('message', 'No message')}")
            logger.error(f"Discord error code: {error_json.get('code', 'No code')}")
        except json.JSONDecodeError:
            pass
            
    except urllib.error.URLError as e:
        logger.exception(f"URLError creating thread: {e.reason}")
    except Exception as e:
        logger.exception(f"Unexpected error creating thread: {type(e).__name__}: {e}")
    
    logger.debug("Thread creation failed, returning None")
    return None


def send_to_thread(thread_id: str, message: DiscordMessage, bot_token: str) -> bool:
    """Send a message to a Discord thread.
    
    Args:
        thread_id: Thread ID
        message: Discord message to send
        bot_token: Discord bot token
        
    Returns:
        True if successful, False otherwise
    """
    logger.debug(f"send_to_thread called - thread_id: {_sanitize_log_input(thread_id)}, message length: {len(str(message))}")
    
    try:
        url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
        data = json.dumps(message).encode("utf-8")
        logger.debug(f"Message data size: {len(data)} bytes")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bot {bot_token}",  # Use full token in actual request
                "Content-Type": "application/json",
                "User-Agent": "Discord-Event-Notifier/1.0"
            }
        )
        
        logger.debug(f"Sending POST request to: {_sanitize_log_input(url)}")
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.status
            logger.debug(f"Discord API response status: {status_code}")
            
            if 200 <= status_code < 300:
                logger.debug("Message sent to thread successfully")
                return True
            else:
                logger.debug(f"Unexpected status code: {status_code}")
                return False
                
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8', errors='ignore')
        logger.error(f"Discord API HTTPError sending to thread: {e.code} - {e.reason}")
        logger.error(f"Error response body: {error_body}")
        
        # Parse error details if possible
        try:
            error_json = json.loads(error_body)
            logger.error(f"Discord error message: {error_json.get('message', 'No message')}")
            logger.error(f"Discord error code: {error_json.get('code', 'No code')}")
        except json.JSONDecodeError:
            pass
            
    except urllib.error.URLError as e:
        logger.error(f"URLError sending to thread: {e.reason}")
    except Exception as e:
        logger.error(f"Unexpected error sending to thread: {type(e).__name__}: {e}")
    
    logger.debug("Failed to send message to thread")
    return False