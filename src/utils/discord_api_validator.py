#!/usr/bin/env python3
"""Discord API validation utilities.

This module provides functions to access Discord API and validate
channel content, specifically for verifying the latest messages
and ensuring proper functionality.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import TypedDict, Optional


class DiscordMessage(TypedDict):
    """Discord message structure."""

    id: str
    content: str
    author: dict[str, str]
    timestamp: str
    embeds: list[dict[str, str]]


class ChannelValidationResult(TypedDict):
    """Channel validation result structure."""

    success: bool
    channel_id: str
    message_count: int
    latest_message: Optional[DiscordMessage]
    validation_timestamp: str
    error_message: Optional[str]
    has_notifier_messages: bool
    notifier_message_count: int


def get_discord_bot_token() -> Optional[str]:
    """Get Discord bot token from environment or config.

    Returns:
        Bot token if available, None otherwise
    """
    # Try environment variable first
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if token:
        return token

    # Try ~/.claude/hooks/.env.discord file
    try:
        env_file = os.path.expanduser("~/.claude/hooks/.env.discord")
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    if line.strip().startswith("DISCORD_BOT_TOKEN="):
                        return line.strip().split("=", 1)[1].strip('"')
    except Exception:
        pass

    return None


def fetch_channel_messages(channel_id: str, limit: int = 50) -> ChannelValidationResult:
    """Fetch recent messages from a Discord channel.

    Args:
        channel_id: Discord channel ID to fetch messages from
        limit: Maximum number of messages to fetch

    Returns:
        Validation result with message information
    """
    current_time = datetime.now(timezone.utc).isoformat()

    # Get bot token
    bot_token = get_discord_bot_token()
    if not bot_token:
        return ChannelValidationResult(
            success=False,
            channel_id=channel_id,
            message_count=0,
            latest_message=None,
            validation_timestamp=current_time,
            error_message="Discord bot token not found",
            has_notifier_messages=False,
            notifier_message_count=0,
        )

    try:
        # Construct Discord API URL
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit={limit}"

        # Create request with authentication
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"Bot {bot_token}")
        request.add_header("User-Agent", "DiscordBot (https://github.com/discord-notifier/discord-notifier, 1.0)")
        request.add_header("Content-Type", "application/json")

        # Make API request
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status != 200:
                return ChannelValidationResult(
                    success=False,
                    channel_id=channel_id,
                    message_count=0,
                    latest_message=None,
                    validation_timestamp=current_time,
                    error_message=f"API returned status {response.status}",
                    has_notifier_messages=False,
                    notifier_message_count=0,
                )

            # Parse response
            data = json.loads(response.read().decode())

            if not isinstance(data, list):
                return ChannelValidationResult(
                    success=False,
                    channel_id=channel_id,
                    message_count=0,
                    latest_message=None,
                    validation_timestamp=current_time,
                    error_message="Unexpected API response format",
                    has_notifier_messages=False,
                    notifier_message_count=0,
                )

            # Analyze messages
            message_count = len(data)
            latest_message = None
            notifier_message_count = 0

            if data:
                # Get latest message
                latest_msg = data[0]
                latest_message = DiscordMessage(
                    id=latest_msg.get("id", ""),
                    content=latest_msg.get("content", ""),
                    author=latest_msg.get("author", {}),
                    timestamp=latest_msg.get("timestamp", ""),
                    embeds=latest_msg.get("embeds", []),
                )

                # Count notifier messages (messages with embeds containing "Discord Notifier")
                for msg in data:
                    embeds = msg.get("embeds", [])
                    for embed in embeds:
                        footer = embed.get("footer", {})
                        footer_text = footer.get("text", "")
                        if "Discord Notifier" in footer_text:
                            notifier_message_count += 1
                            break

            has_notifier_messages = notifier_message_count > 0

            return ChannelValidationResult(
                success=True,
                channel_id=channel_id,
                message_count=message_count,
                latest_message=latest_message,
                validation_timestamp=current_time,
                error_message=None,
                has_notifier_messages=has_notifier_messages,
                notifier_message_count=notifier_message_count,
            )

    except urllib.error.HTTPError as e:
        error_msg = f"HTTP Error {e.code}: {e.reason}"
        if e.code == 403:
            error_msg += " (Bot may not have access to this channel)"
        elif e.code == 404:
            error_msg += " (Channel not found)"
    except urllib.error.URLError as e:
        error_msg = f"Network Error: {e.reason}"
    except json.JSONDecodeError:
        error_msg = "Failed to parse API response as JSON"
    except Exception as e:
        error_msg = f"Unexpected error: {e}"

    return ChannelValidationResult(
        success=False,
        channel_id=channel_id,
        message_count=0,
        latest_message=None,
        validation_timestamp=current_time,
        error_message=error_msg,
        has_notifier_messages=False,
        notifier_message_count=0,
    )


def verify_channel_repeatedly(
    channel_id: str, iterations: int = 3, delay_seconds: int = 2
) -> list[ChannelValidationResult]:
    """Verify channel access repeatedly for real-time validation.

    Args:
        channel_id: Discord channel ID to verify
        iterations: Number of verification attempts
        delay_seconds: Delay between attempts

    Returns:
        List of validation results from each attempt
    """
    import time

    results = []

    for i in range(iterations):
        print(f"🔍 Verification attempt {i + 1}/{iterations}...")
        result = fetch_channel_messages(channel_id)
        results.append(result)

        if result["success"]:
            print(f"✅ Success: Found {result['message_count']} messages")
            if result["has_notifier_messages"]:
                print(f"   📢 {result['notifier_message_count']} Discord Notifier messages detected")
        else:
            print(f"❌ Failed: {result['error_message']}")

        # Wait before next attempt (except for the last one)
        if i < iterations - 1:
            time.sleep(delay_seconds)

    return results


def analyze_channel_health(results: list[ChannelValidationResult]) -> dict[str, str | int | bool]:
    """Analyze channel health from multiple validation attempts.

    Args:
        results: List of validation results

    Returns:
        Health analysis summary
    """
    if not results:
        return {"status": "no_data", "message": "No validation results available"}

    success_count = sum(1 for r in results if r["success"])
    total_attempts = len(results)
    success_rate = success_count / total_attempts if total_attempts > 0 else 0

    latest_result = results[-1]

    # Determine overall health status
    if success_rate >= 0.8:
        status = "healthy"
    elif success_rate >= 0.5:
        status = "partial_issues"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "success_rate": f"{success_rate:.1%}",
        "successful_attempts": success_count,
        "total_attempts": total_attempts,
        "latest_success": latest_result["success"],
        "has_notifier_messages": any(r.get("has_notifier_messages", False) for r in results),
        "max_notifier_messages": max((r.get("notifier_message_count", 0) for r in results), default=0),
        "last_error": latest_result.get("error_message") if not latest_result["success"] else None,
    }


if __name__ == "__main__":
    # Test Discord API validation
    import sys

    # Use the channel ID specified by the user
    CHANNEL_ID = "1391964875600822366"

    print(f"🚀 Starting Discord API validation for channel {CHANNEL_ID}")
    print("=" * 60)

    # Perform repeated verification
    results = verify_channel_repeatedly(CHANNEL_ID, iterations=3, delay_seconds=1)

    print("\n📊 Analysis Results:")
    print("=" * 60)

    # Analyze health
    health = analyze_channel_health(results)
    print(f"Status: {health['status']}")
    print(f"Success Rate: {health['success_rate']}")
    print(f"Discord Notifier Messages Found: {health['has_notifier_messages']}")

    if health["has_notifier_messages"]:
        print(f"Max Notifier Messages: {health['max_notifier_messages']}")

    if health.get("last_error"):
        print(f"Last Error: {health['last_error']}")

    # Show latest message info if available
    latest_result = results[-1] if results else None
    if latest_result and latest_result["success"] and latest_result["latest_message"]:
        latest_msg = latest_result["latest_message"]
        print(f"\n📝 Latest Message Info:")
        print(f"Message ID: {latest_msg['id']}")
        print(f"Author: {latest_msg['author'].get('username', 'Unknown')}")
        print(f"Timestamp: {latest_msg['timestamp']}")
        print(f"Content Preview: {latest_msg['content'][:100]}...")
        print(f"Embeds Count: {len(latest_msg['embeds'])}")

    print("\n" + "=" * 60)
    print("Discord API validation completed!")
