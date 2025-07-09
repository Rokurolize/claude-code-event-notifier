#!/usr/bin/env python3
"""Discord message sender for Discord Notifier.

This module handles sending formatted messages to Discord through
various methods including webhooks, bot API, and thread management.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.core.constants import EventTypes
from src.core.exceptions import DiscordAPIError
from src.core.http_client import DiscordMessage, HTTPClient
from src.handlers.thread_manager import SESSION_THREAD_CACHE, get_or_create_thread

if TYPE_CHECKING:
    from src.core.http_client import DiscordThreadMessage

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
    thread_message: DiscordMessage = {"embeds": message.get("embeds", [])}

    try:
        if ctx.config["webhook_url"]:
            return ctx.http_client.post_webhook_to_thread(ctx.config["webhook_url"], thread_message, thread_id)
        if ctx.config["bot_token"]:
            url = f"https://discord.com/api/v10/channels/{thread_id}/messages"
            return ctx.http_client.post_bot_api(url, thread_message, ctx.config["bot_token"])
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
        display_message = (
            message.get("content", "").replace(f"<@{ctx.config['mention_user_id']}> ", "") or "System notification"
        )
    else:  # Stop event
        display_message = "Session ended"

    # Create mention-only message
    mention_message: DiscordMessage = {"content": f"<@{ctx.config['mention_user_id']}> {display_message}"}

    try:
        if ctx.config["webhook_url"]:
            return ctx.http_client.post_webhook(ctx.config["webhook_url"], mention_message)
        if ctx.config["bot_token"] and ctx.config["channel_id"]:
            url = f"https://discord.com/api/v10/channels/{ctx.config['channel_id']}/messages"
            return ctx.http_client.post_bot_api(url, mention_message, ctx.config["bot_token"])
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
    if event_type == EventTypes.STOP.value and thread_id and ctx.config.get("bot_token"):
        try:
            if ctx.http_client.archive_thread(thread_id, ctx.config["bot_token"]):
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
                return ctx.http_client.post_webhook_to_thread(ctx.config["webhook_url"], message, thread_id)
            except DiscordAPIError:
                ctx.logger.warning("Failed to send to thread, falling back to regular channel")
                return None

    elif ctx.config["channel_type"] == "forum" and ctx.config["webhook_url"]:
        # Create forum thread with first message
        thread_name = f"{ctx.config['thread_prefix']} {session_id[:8]}"
        thread_message: DiscordThreadMessage = {
            "embeds": message.get("embeds", []),
            "thread_name": thread_name,
        }

        try:
            thread_id = ctx.http_client.create_forum_thread(ctx.config["webhook_url"], thread_message, thread_name)
            if thread_id:
                SESSION_THREAD_CACHE[session_id] = thread_id
                ctx.logger.info("Created forum thread %s for session %s", thread_id, session_id)
                return True
            ctx.logger.warning("Forum thread creation failed, falling back to regular channel")
        except DiscordAPIError:
            ctx.logger.warning("Forum thread creation failed, falling back to regular channel")

    return None


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
    if ctx.config["webhook_url"]:
        try:
            return ctx.http_client.post_webhook(ctx.config["webhook_url"], message)
        except DiscordAPIError:
            pass  # Fall through to bot API

    # Try bot API as fallback
    if ctx.config["bot_token"] and ctx.config["channel_id"]:
        try:
            url = f"https://discord.com/api/v10/channels/{ctx.config['channel_id']}/messages"
            return ctx.http_client.post_bot_api(url, message, ctx.config["bot_token"])
        except DiscordAPIError:
            pass

    return False
