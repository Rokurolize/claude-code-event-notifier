"""Message sending functionality for Discord Notifier.

This module handles sending messages to Discord via webhook or bot API,
with support for threads, message splitting, and special event handling.
"""

import logging
import time
from typing import Any

# Try to import types
try:
    from src.type_defs.config import Config
    from src.type_defs.discord import DiscordMessage
except ImportError:
    # Fallback if modules not available
    from discord_notifier import Config, DiscordMessage  # type: ignore

# Try to import HTTPClient
try:
    from src.core.http_client import HTTPClient
except ImportError:
    from discord_notifier import HTTPClient  # type: ignore

# Try to import constants
try:
    from src.constants import EventTypes, DiscordLimits
except ImportError:
    from discord_notifier import EventTypes, DiscordLimits  # type: ignore

# Try to import thread manager
try:
    from src.core.thread_manager import get_or_create_thread
except ImportError:
    from discord_notifier import get_or_create_thread  # type: ignore


def send_to_discord(
    message: DiscordMessage,
    config: Config,
    logger: logging.Logger,
    http_client: HTTPClient,
    session_id: str = "",
    event_type: str = "",
) -> bool:
    """Send message to Discord via webhook or bot API, with optional thread support.

    For Stop/Notification events:
    - Send embed-only message to thread
    - Send mention-only message to main channel
    - Archive thread for Stop events
    """
    # Split message if needed (for long content)
    messages = _split_embed_if_needed(message)
    
    # If multiple messages, send them sequentially
    if len(messages) > 1:
        logger.info("Splitting long message into %d parts", len(messages))
        all_success = True
        for i, msg in enumerate(messages):
            # Add small delay between messages to avoid rate limiting
            if i > 0:
                time.sleep(0.5)
            
            # Send each part using the regular logic
            success = _send_single_message(msg, config, logger, http_client, session_id, event_type)
            if not success:
                all_success = False
                logger.error("Failed to send message part %d", i + 1)
        return all_success
    
    # Single message, use regular logic
    return _send_single_message(message, config, logger, http_client, session_id, event_type)


def _split_embed_if_needed(message: DiscordMessage) -> list[DiscordMessage]:
    """Split a message if its embed description exceeds Discord limits.
    
    Args:
        message: Original Discord message with embeds
        
    Returns:
        List of messages, split if necessary
    """
    if not message.get("embeds") or not message["embeds"]:
        return [message]
    
    embed = message["embeds"][0]
    description = embed.get("description", "")
    
    # If within limits, return as-is
    if len(description) <= DiscordLimits.MAX_DESCRIPTION_LENGTH:
        return [message]
    
    # Split the description
    messages: list[DiscordMessage] = []
    remaining_desc = description
    part_num = 1
    
    while remaining_desc:
        # Calculate how much we can fit
        chunk_size = DiscordLimits.MAX_DESCRIPTION_LENGTH
        
        # For continuation messages, reserve space for part indicator
        if part_num > 1:
            chunk_size -= 50  # Space for "... (continued from previous message)"
            
        # Find a good break point (prefer newline, then space)
        if len(remaining_desc) > chunk_size:
            # Look for newline near the end
            newline_pos = remaining_desc.rfind('\n', chunk_size - 200, chunk_size)
            if newline_pos > 0:
                chunk_size = newline_pos + 1
            else:
                # Look for space
                space_pos = remaining_desc.rfind(' ', chunk_size - 100, chunk_size)
                if space_pos > 0:
                    chunk_size = space_pos + 1
        
        # Extract chunk
        chunk = remaining_desc[:chunk_size]
        remaining_desc = remaining_desc[chunk_size:]
        
        # Create new message with modified embed
        new_embed = embed.copy()
        
        if part_num == 1:
            # First part keeps original title
            new_embed["description"] = chunk
            if remaining_desc:
                new_embed["description"] += "\n\n... (continued in next message)"
        else:
            # Subsequent parts get modified title and description
            original_title = embed.get("title", "Continued")
            new_embed["title"] = f"{original_title} (Part {part_num})"
            new_embed["description"] = "... (continued from previous message)\n\n" + chunk
            if remaining_desc:
                new_embed["description"] += "\n\n... (continued in next message)"
            
            # Remove fields from continuation messages to save space
            new_embed["fields"] = None
        
        # Remove footer from all but the last part
        if remaining_desc:
            new_embed["footer"] = None
            new_embed["timestamp"] = None
        
        new_message: DiscordMessage = {
            "embeds": [new_embed],
            "content": message.get("content")
        }
        messages.append(new_message)
        part_num += 1
    
    return messages


def _send_single_message(
    message: DiscordMessage,
    config: Config,
    logger: logging.Logger,
    http_client: HTTPClient,
    session_id: str = "",
    event_type: str = "",
) -> bool:
    """Send a single message to Discord (internal helper).
    
    Args:
        message: Discord message to send
        config: Configuration
        logger: Logger instance
        http_client: HTTP client for Discord API
        session_id: Optional session ID for thread management
        event_type: Optional event type for special handling
        
    Returns:
        bool: True if message was successfully sent
    """
    # Special handling for Stop and Notification events
    if event_type in [EventTypes.STOP.value, EventTypes.NOTIFICATION.value] and config["use_threads"] and session_id:
        return _send_stop_or_notification_event(message, config, logger, http_client, session_id, event_type)

    # Regular event handling (PreToolUse, PostToolUse, etc.)
    # Try thread messaging first
    thread_result = _send_to_thread(message, config, logger, http_client, session_id)
    if thread_result is not None:
        return thread_result

    # Fall back to regular channel messaging
    return _send_to_regular_channel(message, config, http_client)


def _send_stop_or_notification_event(
    message: DiscordMessage,
    config: Config,
    logger: logging.Logger,
    http_client: HTTPClient,
    session_id: str,
    event_type: str,
) -> bool:
    """Handle special Stop/Notification event sending with dual messages.
    
    Args:
        message: Discord message to send
        config: Configuration
        logger: Logger instance
        http_client: HTTP client for Discord API
        session_id: Session ID for thread management
        event_type: Event type (Stop or Notification)
        
    Returns:
        bool: True if message was successfully sent
    """
    # 1. Send embeds-only message to thread (no mention)
    thread_id = get_or_create_thread(session_id, config, http_client, logger)
    embeds_only_message: DiscordMessage = {"embeds": message.get("embeds", [])}
    thread_success = False

    if thread_id:
        if config["webhook_url"]:
            thread_success = http_client.send_webhook_to_thread(
                config["webhook_url"], embeds_only_message, thread_id
            )
        elif config["bot_token"] and thread_id:
            thread_success = http_client.send_bot_message(
                config["bot_token"], thread_id, embeds_only_message
            )
    else:
        logger.warning("No thread found/created for Stop/Notification event in session %s", session_id)

    # 2. Send mention-only message to main channel
    main_channel_success = False
    if message.get("content"):  # Only if there's a mention
        mention_only_message: DiscordMessage = {"content": message["content"]}
        if config["webhook_url"]:
            main_channel_success = http_client.send_webhook_message(
                config["webhook_url"], mention_only_message
            )
        elif config["bot_token"] and config["channel_id"]:
            main_channel_success = http_client.send_bot_message(
                config["bot_token"], config["channel_id"], mention_only_message
            )

    # 3. Archive thread for Stop events
    if event_type == EventTypes.STOP.value and thread_id and config["bot_token"]:
        try:
            http_client.archive_thread(thread_id, config["bot_token"])
            logger.info("Archived thread %s for ended session %s", thread_id, session_id)
        except Exception as e:
            logger.warning("Failed to archive thread %s: %s", thread_id, e)

    # Success if at least the thread message was sent (main channel mention is optional)
    return thread_success


def _send_to_thread(
    message: DiscordMessage,
    config: Config,
    logger: logging.Logger,
    http_client: HTTPClient,
    session_id: str = "",
) -> bool | None:
    """Try to send message to a thread.
    
    Args:
        message: Discord message to send
        config: Configuration
        logger: Logger instance
        http_client: HTTP client for Discord API
        session_id: Session ID for thread lookup
        
    Returns:
        bool if message was sent (True) or failed (False)
        None if thread messaging is not applicable
    """
    if not config["use_threads"] or not session_id:
        return None

    thread_id = get_or_create_thread(session_id, config, http_client, logger)
    if not thread_id:
        logger.debug("No thread available for session %s", session_id)
        return None

    # Try webhook first
    if config["webhook_url"]:
        if http_client.send_webhook_to_thread(config["webhook_url"], message, thread_id):
            return True
        logger.warning("Failed to send to thread %s via webhook", thread_id)
        return False

    # Try bot API
    if config["bot_token"]:
        if http_client.send_bot_message(config["bot_token"], thread_id, message):
            return True
        logger.warning("Failed to send to thread %s via bot API", thread_id)
        return False

    return None


def _send_to_regular_channel(
    message: DiscordMessage, config: Config, http_client: HTTPClient
) -> bool:
    """Send message to regular Discord channel.
    
    Args:
        message: Discord message to send
        config: Configuration
        http_client: HTTP client for Discord API
        
    Returns:
        bool: True if message was successfully sent
    """
    if config["webhook_url"]:
        return http_client.send_webhook_message(config["webhook_url"], message)

    if config["bot_token"] and config["channel_id"]:
        return http_client.send_bot_message(
            config["bot_token"], config["channel_id"], message
        )

    return False


# Export all public functions
__all__ = [
    'send_to_discord',
    '_split_embed_if_needed',
    '_send_single_message',
    '_send_stop_or_notification_event',
    '_send_to_thread',
    '_send_to_regular_channel',
]