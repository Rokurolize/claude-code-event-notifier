#!/usr/bin/env python3
"""Discord message sender for Discord Notifier.

This module handles sending formatted messages to Discord through
various methods including webhooks, bot API, and thread management.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.constants import DiscordLimits, EventTypes
from src.core.exceptions import DiscordAPIError
from src.core.http_client import DiscordMessage, HTTPClient
from src.handlers.thread_manager import SESSION_THREAD_CACHE, get_or_create_thread

if TYPE_CHECKING:
    from src.core.http_client import DiscordEmbed, DiscordThreadMessage

# Type alias for configuration
Config = dict[str, str | int | bool]


@dataclass
class DiscordContext:
    """Context object containing Discord API resources."""

    config: Config
    logger: logging.Logger
    http_client: HTTPClient


def _send_embed_to_thread(
    thread_id: str,
    message: DiscordMessage,
    ctx: DiscordContext,
) -> bool:
    """Send embed-only message to thread.

    Args:
        thread_id: Discord thread ID
        message: Original message containing embeds
        ctx: Discord context with config, logger, and HTTP client

    Returns:
        bool: True if successful, False otherwise
    """
    thread_message: DiscordMessage = {
        "content": None,
        "embeds": message.get("embeds", [])
    }

    try:
        webhook_url = ctx.config.get("webhook_url")
        if webhook_url and isinstance(webhook_url, str):
            return ctx.http_client.post_webhook_to_thread(webhook_url, thread_message, thread_id)
        bot_token = ctx.config.get("bot_token")
        if bot_token and isinstance(bot_token, str):
            url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
            return ctx.http_client.post_bot_api(url, thread_message, bot_token)
    except DiscordAPIError as e:
        ctx.logger.warning("Failed to send embed to thread %s: %s", thread_id, e)

    return False


def _send_mention_to_channel(
    message: DiscordMessage,
    event_type: str,
    ctx: DiscordContext,
) -> bool:
    """Send mention-only message to main channel.

    Args:
        message: Original message
        event_type: Type of event being processed
        ctx: Discord context with config, logger, and HTTP client

    Returns:
        bool: True if successful, False otherwise
    """
    if not ctx.config.get("mention_user_id"):
        return False

    # Extract display message based on event type
    if event_type == EventTypes.NOTIFICATION.value:
        original_content = message.get("content", "")
        if original_content:
            display_message = original_content.replace(f"<@{ctx.config['mention_user_id']}> ", "") or "System notification"
        else:
            display_message = "System notification"
    else:  # Stop event
        display_message = "Session ended"

    # Create mention-only message
    mention_message: DiscordMessage = {
        "content": f"<@{ctx.config['mention_user_id']}> {display_message}",
        "embeds": None
    }

    try:
        webhook_url = ctx.config.get("webhook_url")
        if webhook_url and isinstance(webhook_url, str):
            return ctx.http_client.post_webhook(webhook_url, mention_message)
        
        bot_token = ctx.config.get("bot_token")
        channel_id = ctx.config.get("channel_id")
        if bot_token and isinstance(bot_token, str) and channel_id:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            return ctx.http_client.post_bot_api(url, mention_message, bot_token)
    except DiscordAPIError as e:
        ctx.logger.warning("Failed to send mention to main channel: %s", e)

    return False


def _handle_stop_notification_events(
    message: DiscordMessage,
    session_id: str,
    event_type: str,
    ctx: DiscordContext,
) -> bool:
    """Handle special logic for Stop and Notification events.

    Args:
        message: Discord message to send
        session_id: Session identifier
        event_type: Type of event
        ctx: Discord context with config, logger, and HTTP client

    Returns:
        bool: True if message was sent successfully
    """
    success = False

    # 1. Send embed to thread (if exists)
    thread_id = get_or_create_thread(session_id, ctx.config, ctx.http_client, ctx.logger)
    if thread_id and _send_embed_to_thread(thread_id, message, ctx):
        ctx.logger.debug("Sent embed to thread %s for %s event", thread_id, event_type)
        success = True

    # 2. Send mention-only message to main channel
    if _send_mention_to_channel(message, event_type, ctx):
        ctx.logger.debug("Sent mention to main channel for %s event", event_type)
        success = True

    # 3. Archive thread for Stop events
    bot_token = ctx.config.get("bot_token")
    if event_type == EventTypes.STOP.value and thread_id and bot_token and isinstance(bot_token, str):
        try:
            if ctx.http_client.archive_thread(thread_id, bot_token):
                ctx.logger.info("Archived thread %s after session %s ended", thread_id, session_id)
                SESSION_THREAD_CACHE.pop(session_id, None)
            else:
                ctx.logger.warning("Failed to archive thread %s", thread_id)
        except DiscordAPIError as e:
            ctx.logger.warning("Failed to archive thread %s: %s", thread_id, e)

    return success


def _handle_thread_messaging(
    message: DiscordMessage,
    session_id: str,
    ctx: DiscordContext,
) -> bool | None:
    """Handle thread-based messaging for regular events.

    Args:
        message: Discord message to send
        session_id: Session identifier
        ctx: Discord context with config, logger, and HTTP client

    Returns:
        bool if message was sent, None if fallback to regular channel needed
    """
    thread_id = get_or_create_thread(session_id, ctx.config, ctx.http_client, ctx.logger)

    if thread_id:
        # Send to existing thread
        if ctx.config["webhook_url"]:
            try:
                webhook_url = ctx.config.get("webhook_url")
                if not isinstance(webhook_url, str):
                    return None
                return ctx.http_client.post_webhook_to_thread(webhook_url, message, thread_id)
            except DiscordAPIError:
                ctx.logger.warning("Failed to send to thread, falling back to regular channel")
                return None

    elif ctx.config.get("channel_type") == "forum":
        # Create forum thread with first message
        webhook_url = ctx.config.get("webhook_url")
        if webhook_url and isinstance(webhook_url, str):
            thread_name = f"{ctx.config.get('thread_prefix', 'Session')} {session_id[:8]}"
            thread_message: DiscordThreadMessage = {
                "embeds": message.get("embeds", []),
                "thread_name": thread_name,
            }

            try:
                thread_id = ctx.http_client.create_forum_thread(webhook_url, thread_message, thread_name)
                if thread_id:
                    SESSION_THREAD_CACHE[session_id] = thread_id
                    ctx.logger.info("Created forum thread %s for session %s", thread_id, session_id)
                    return True
                ctx.logger.warning("Forum thread creation failed, falling back to regular channel")
            except DiscordAPIError:
                ctx.logger.warning("Forum thread creation failed, falling back to regular channel")

    return None


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
    if not description or len(description) <= DiscordLimits.MAX_DESCRIPTION_LENGTH:
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
                new_embed["description"] = chunk + "\n\n... (continued in next message)"
        else:
            # Subsequent parts get modified title and description
            original_title = embed.get("title", "Continued")
            new_embed["title"] = f"{original_title} (Part {part_num})"
            if remaining_desc:
                new_embed["description"] = "... (continued from previous message)\n\n" + chunk + "\n\n... (continued in next message)"
            else:
                new_embed["description"] = "... (continued from previous message)\n\n" + chunk
            
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


def send_to_discord(
    message: DiscordMessage,
    ctx: DiscordContext,
    session_id: str = "",
    event_type: str = "",
) -> bool:
    """Send message to Discord via webhook or bot API, with optional thread support.

    This function handles the complex logic of sending messages to Discord,
    including thread management, special handling for Stop/Notification events,
    and fallback strategies when primary methods fail.

    Args:
        message: Discord message to send containing embeds and optional content
        ctx: Discord context with config, logger, and HTTP client
        session_id: Optional session ID for thread management
        event_type: Optional event type for special handling

    Returns:
        bool: True if message was successfully sent, False otherwise
    """
    # Split message if needed (for long content)
    messages = _split_embed_if_needed(message)
    
    # If multiple messages, send them sequentially
    if len(messages) > 1:
        ctx.logger.info("Splitting long message into %d parts", len(messages))
        all_success = True
        for i, msg in enumerate(messages):
            # Add small delay between messages to avoid rate limiting
            if i > 0:
                import time
                time.sleep(0.5)
            
            # Send each part using the regular logic
            success = _send_single_message(msg, ctx, session_id, event_type)
            if not success:
                all_success = False
                ctx.logger.error("Failed to send message part %d", i + 1)
        return all_success
    
    # Single message, use regular logic
    return _send_single_message(message, ctx, session_id, event_type)


def _send_single_message(
    message: DiscordMessage,
    ctx: DiscordContext,
    session_id: str = "",
    event_type: str = "",
) -> bool:
    """Send a single message to Discord (internal helper).
    
    Args:
        message: Discord message to send
        ctx: Discord context
        session_id: Optional session ID for thread management
        event_type: Optional event type for special handling
        
    Returns:
        bool: True if message was successfully sent
    """
    # Special handling for Stop and Notification events
    if (
        event_type in [EventTypes.STOP.value, EventTypes.NOTIFICATION.value]
        and ctx.config["use_threads"]
        and session_id
    ):
        return _handle_stop_notification_events(message, session_id, event_type, ctx)

    # Regular event handling with thread support
    if ctx.config["use_threads"] and session_id:
        result = _handle_thread_messaging(message, session_id, ctx)
        if result is not None:
            return result
        # If None, fall through to regular channel messaging

    # Regular channel messaging (no threads or fallback)
    # Try webhook first
    webhook_url = ctx.config.get("webhook_url")
    if webhook_url and isinstance(webhook_url, str):
        try:
            return ctx.http_client.post_webhook(webhook_url, message)
        except DiscordAPIError:
            pass  # Fall through to bot API

    # Try bot API as fallback
    bot_token = ctx.config.get("bot_token")
    channel_id = ctx.config.get("channel_id")
    if bot_token and isinstance(bot_token, str) and channel_id:
        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            return ctx.http_client.post_bot_api(url, message, bot_token)
        except DiscordAPIError:
            pass

    return False
