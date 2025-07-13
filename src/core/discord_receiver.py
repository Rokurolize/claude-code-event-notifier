#!/usr/bin/env python3
"""Discord message receiver for validation and testing.

This module provides functionality to receive and parse Discord messages
using the bot API, enabling automatic verification of sent notifications.
"""

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Optional, TypedDict

from src.core.config import ConfigLoader
from src.core.http_client import HTTPClient
from src.utils.astolfo_logger import AstolfoLogger
from src.utils.datetime_utils import get_user_datetime


class DiscordMessage(TypedDict):
    """Structure for Discord message from API."""
    id: str
    channel_id: str
    author: dict[str, Any]
    content: str
    timestamp: str
    embeds: list[dict[str, Any]]
    type: int


class MessageFilter(TypedDict, total=False):
    """Filter criteria for message retrieval."""
    limit: int
    before: Optional[str]
    after: Optional[str]
    around: Optional[str]


class DiscordReceiver:
    """Discord message receiver using bot API."""
    
    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        """Initialize Discord receiver.
        
        Args:
            config: Optional configuration dict, loads from ConfigLoader if None
        """
        self.logger = AstolfoLogger(__name__)
        
        if config is None:
            config_loader = ConfigLoader()
            config = config_loader.load()
        
        self.config = config
        self.http_client = HTTPClient(config)
        
        # Validate bot token is available for receiving
        if not config.get("discord_token"):
            self.logger.warning("No Discord bot token configured - receiving will not work")
            self.bot_token = None
        else:
            self.bot_token = config["discord_token"]
        
        self.channel_id = config.get("discord_channel_id")
        
        self.logger.info(
            "Discord receiver initialized",
            has_bot_token=bool(self.bot_token),
            has_channel_id=bool(self.channel_id)
        )
    
    def get_channel_messages(
        self, 
        channel_id: Optional[str] = None,
        limit: int = 10,
        time_window_minutes: int = 5
    ) -> list[DiscordMessage]:
        """Get recent messages from a Discord channel.
        
        Args:
            channel_id: Discord channel ID, uses default if None
            limit: Maximum number of messages to retrieve (max 100)
            time_window_minutes: Only get messages from last N minutes
            
        Returns:
            List of Discord messages
            
        Raises:
            urllib.error.HTTPError: If Discord API request fails
            ValueError: If channel_id is invalid
        """
        if channel_id is None:
            channel_id = self.channel_id
            
        if not channel_id:
            raise ValueError("No channel ID provided and no default configured")
        
        if not self.bot_token:
            raise ValueError("No Discord bot token configured - cannot receive messages")
        
        # Calculate time filter for recent messages
        cutoff_time = get_user_datetime() - timedelta(minutes=time_window_minutes)
        
        self.logger.info(
            "Retrieving channel messages",
            channel_id=channel_id,
            limit=limit,
            time_window_minutes=time_window_minutes,
            cutoff_time=cutoff_time.isoformat()
        )
        
        # Discord API endpoint
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        
        # Build query parameters
        params = {
            "limit": min(limit, 100)  # Discord API limit
        }
        
        # Make API request
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        try:
            query_string = urllib.parse.urlencode(params)
            full_url = f"{url}?{query_string}"
            
            req = urllib.request.Request(full_url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read()
                messages_raw = json.loads(response_data.decode('utf-8'))
            
            # Filter messages by time window
            filtered_messages = []
            for msg_raw in messages_raw:
                msg_time_str = msg_raw.get("timestamp", "")
                try:
                    # Parse Discord timestamp (ISO format with timezone)
                    msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00'))
                    
                    # Convert to user timezone for comparison
                    msg_time_user = msg_time.astimezone(cutoff_time.tzinfo)
                    
                    if msg_time_user >= cutoff_time:
                        # Convert to our DiscordMessage format
                        typed_message: DiscordMessage = {
                            "id": str(msg_raw.get("id", "")),
                            "channel_id": str(msg_raw.get("channel_id", "")),
                            "author": msg_raw.get("author", {}),
                            "content": str(msg_raw.get("content", "")),
                            "timestamp": msg_time_str,
                            "embeds": msg_raw.get("embeds", []),
                            "type": int(msg_raw.get("type", 0))
                        }
                        filtered_messages.append(typed_message)
                        
                except (ValueError, TypeError) as e:
                    self.logger.warning(
                        "Failed to parse message timestamp",
                        message_id=msg_raw.get("id"),
                        timestamp=msg_time_str,
                        error=str(e)
                    )
                    continue
            
            self.logger.info(
                "Channel messages retrieved",
                channel_id=channel_id,
                total_messages=len(messages_raw),
                filtered_messages=len(filtered_messages),
                time_window_minutes=time_window_minutes
            )
            
            return filtered_messages
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "No error details"
            self.logger.error(
                "Discord API HTTP error",
                status_code=e.code,
                reason=e.reason,
                error_body=error_body,
                channel_id=channel_id
            )
            raise RuntimeError(f"Discord API error {e.code}: {e.reason}") from e
            
        except urllib.error.URLError as e:
            self.logger.error(
                "Discord API network error", 
                error=str(e),
                channel_id=channel_id
            )
            raise RuntimeError(f"Network error: {e}") from e
    
    def get_thread_messages(
        self,
        thread_id: str,
        limit: int = 10,
        time_window_minutes: int = 5
    ) -> list[DiscordMessage]:
        """Get recent messages from a Discord thread.
        
        Args:
            thread_id: Discord thread ID
            limit: Maximum number of messages to retrieve
            time_window_minutes: Only get messages from last N minutes
            
        Returns:
            List of Discord messages from the thread
        """
        self.logger.info(
            "Retrieving thread messages",
            thread_id=thread_id,
            limit=limit,
            time_window_minutes=time_window_minutes
        )
        
        # Threads use the same endpoint as channels
        return self.get_channel_messages(
            channel_id=thread_id,
            limit=limit, 
            time_window_minutes=time_window_minutes
        )
    
    def find_messages_by_embed_title(
        self,
        title_pattern: str,
        channel_id: Optional[str] = None,
        limit: int = 20,
        time_window_minutes: int = 10
    ) -> list[DiscordMessage]:
        """Find messages containing embeds with specific title pattern.
        
        Args:
            title_pattern: Pattern to search for in embed titles
            channel_id: Channel to search in, uses default if None
            limit: Maximum messages to check
            time_window_minutes: Time window for search
            
        Returns:
            List of messages with matching embed titles
        """
        self.logger.info(
            "Searching for messages by embed title",
            title_pattern=title_pattern,
            channel_id=channel_id or self.channel_id,
            limit=limit
        )
        
        messages = self.get_channel_messages(
            channel_id=channel_id,
            limit=limit,
            time_window_minutes=time_window_minutes
        )
        
        matching_messages = []
        for message in messages:
            for embed in message.get("embeds", []):
                embed_title = embed.get("title", "")
                if title_pattern.lower() in embed_title.lower():
                    matching_messages.append(message)
                    break  # Found match in this message, no need to check other embeds
        
        self.logger.info(
            "Embed title search completed",
            title_pattern=title_pattern,
            total_checked=len(messages),
            matches_found=len(matching_messages)
        )
        
        return matching_messages
    
    def find_latest_subagent_message(
        self,
        subagent_id: str,
        channel_id: Optional[str] = None,
        time_window_minutes: int = 5
    ) -> Optional[DiscordMessage]:
        """Find the most recent message from a specific subagent.
        
        Args:
            subagent_id: Subagent identifier to search for
            channel_id: Channel to search in
            time_window_minutes: Time window for search
            
        Returns:
            Most recent message from the subagent, or None if not found
        """
        self.logger.info(
            "Searching for latest subagent message",
            subagent_id=subagent_id,
            channel_id=channel_id or self.channel_id
        )
        
        # Search for "Subagent Completed" messages
        messages = self.find_messages_by_embed_title(
            title_pattern="Subagent Completed",
            channel_id=channel_id,
            limit=30,
            time_window_minutes=time_window_minutes
        )
        
        # Filter by subagent ID in embed description
        for message in messages:
            for embed in message.get("embeds", []):
                description = embed.get("description", "")
                if f"Subagent ID:** {subagent_id}" in description:
                    self.logger.info(
                        "Found latest subagent message",
                        subagent_id=subagent_id,
                        message_id=message["id"],
                        timestamp=message["timestamp"]
                    )
                    return message
        
        self.logger.warning(
            "No recent message found for subagent",
            subagent_id=subagent_id,
            time_window_minutes=time_window_minutes
        )
        return None