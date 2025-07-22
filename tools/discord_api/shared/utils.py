#!/usr/bin/env python3
"""Discord API utilities.

Common utilities for Discord API interaction across all tools.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from .config import get_discord_bot_token


def make_discord_request(
    url: str,
    method: str = "GET",
    data: Optional[dict[str, Any]] = None,
    timeout: int = 10,
) -> tuple[bool, Optional[dict[str, Any]], Optional[str]]:
    """Make authenticated Discord API request.

    Args:
        url: Discord API URL
        method: HTTP method (GET, POST, etc.)
        data: Request payload (for POST/PUT requests)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success, response_data, error_message)
    """
    token = get_discord_bot_token()
    if not token:
        return False, None, "Discord bot token not found"

    try:
        # Prepare request
        request_data = None
        if data:
            request_data = json.dumps(data).encode("utf-8")

        request = urllib.request.Request(url, data=request_data, method=method)
        request.add_header("Authorization", f"Bot {token}")
        request.add_header("User-Agent", "DiscordAPITools/1.0")
        
        if request_data:
            request.add_header("Content-Type", "application/json")

        # Make request
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if 200 <= response.status < 300:
                content = response.read().decode("utf-8")
                if content:
                    try:
                        response_data = json.loads(content)
                        return True, response_data, None
                    except json.JSONDecodeError:
                        return True, {"raw_content": content}, None
                else:
                    return True, {}, None
            else:
                return False, None, f"HTTP {response.status}: Request failed"

    except urllib.error.HTTPError as e:
        error_msg = f"HTTP {e.code}: {e.reason}"
        
        # Try to parse error response
        try:
            error_body = e.read().decode("utf-8")
            error_data = json.loads(error_body)
            error_details = format_discord_api_error(error_data)
            if error_details:
                error_msg += f" - {error_details}"
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            pass

        return False, None, error_msg

    except urllib.error.URLError as e:
        return False, None, f"Network error: {e.reason}"

    except Exception as e:
        return False, None, f"Unexpected error: {e}"


def format_discord_api_error(error_data: dict[str, Any]) -> Optional[str]:
    """Format Discord API error for human-readable display.

    Args:
        error_data: Discord API error response

    Returns:
        Formatted error message or None if no specific error code
    """
    error_code = error_data.get("code")
    if not error_code:
        return None

    # Common Discord API error codes
    error_messages = {
        10003: "Unknown Channel: Channel does not exist or bot lacks access",
        10004: "Unknown Guild: Guild does not exist",
        10008: "Unknown Message: Message does not exist",
        10013: "Unknown User: User does not exist",
        20001: "Bots cannot use this endpoint",
        20028: "Cannot delete a message authored by another user",
        30001: "Maximum number of guilds reached",
        30003: "Maximum number of friends reached",
        40001: "Unauthorized: Invalid token",
        40002: "Authentication required",
        40005: "Request entity too large",
        40006: "Feature temporarily disabled server-side",
        40007: "The user is banned from this guild",
        50001: "Missing Access: Bot lacks permission to access this resource",
        50003: "Cannot execute action on a DM channel",
        50004: "Guild widget disabled",
        50005: "Cannot edit a message authored by another user",
        50006: "Cannot send an empty message",
        50007: "Cannot send messages to this user",
        50008: "Cannot send messages in a voice channel",
        50013: "Missing Permissions: Bot lacks required permissions",
        50014: "Invalid authentication token",
        50015: "Note too long",
        50016: "Provided too few or too many messages to delete",
        50019: "A message can only be pinned to the channel it was sent in",
        50021: "Invite code is either invalid or taken",
        50025: "Invalid OAuth2 access token",
        50034: "A message provided was too old to bulk delete",
        50035: "Invalid form body",
        50041: "Invalid API version",
        50045: "File uploaded exceeds the maximum size",
        50081: "Invalid webhook token",
        50095: "Invalid command",
        60003: "Two factor is required for this operation",
    }

    error_message = error_messages.get(error_code)
    if error_message:
        return f"Code {error_code}: {error_message}"

    # Fallback to generic message
    message = error_data.get("message", "Unknown error")
    return f"Code {error_code}: {message}"


def print_api_response(
    success: bool,
    data: Optional[dict[str, Any]],
    error: Optional[str],
    operation: str = "API request",
) -> None:
    """Print API response in a consistent format.

    Args:
        success: Whether the request was successful
        data: Response data (if successful)
        error: Error message (if failed)
        operation: Description of the operation for logging
    """
    if success:
        print(f"✅ {operation} - Success")
        if data:
            print(f"   Response: {json.dumps(data, indent=2)}")
    else:
        print(f"❌ {operation} - Failed")
        if error:
            print(f"   Error: {error}")


def extract_message_info(message_data: dict[str, Any]) -> dict[str, Any]:
    """Extract key information from Discord message data.

    Args:
        message_data: Raw message data from Discord API

    Returns:
        Simplified message information
    """
    return {
        "id": message_data.get("id", ""),
        "content": message_data.get("content", ""),
        "author": {
            "id": message_data.get("author", {}).get("id", ""),
            "username": message_data.get("author", {}).get("username", "Unknown"),
            "bot": message_data.get("author", {}).get("bot", False),
        },
        "timestamp": message_data.get("timestamp", ""),
        "embeds_count": len(message_data.get("embeds", [])),
        "attachments_count": len(message_data.get("attachments", [])),
        "reactions_count": len(message_data.get("reactions", [])),
    }