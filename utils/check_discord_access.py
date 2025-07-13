#!/usr/bin/env python3
"""Check Discord API access and permissions."""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Add parent directory to Python path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.astolfo_logger import AstolfoLogger


def check_api_access(url: str, token: str, logger: AstolfoLogger) -> None:
    """Check Discord API access with detailed error reporting.

    Args:
        url: Discord API URL to test
        token: Bot token for authentication
        logger: AstolfoLogger instance for logging
    """
    print(f"Testing: {url}")
    logger.debug("Testing Discord API access", {"url": url})

    try:
        headers = {"Authorization": f"Bot {token}"}
        request = urllib.request.Request(url, headers=headers)  # noqa: S310

        with urllib.request.urlopen(request) as response:  # type: ignore[misc] # noqa: S310
            print(f"✓ Success: {response.status}")
            data = json.loads(response.read().decode())
            print(f"Response: {json.dumps(data, indent=2)}")
            logger.info("Discord API access successful", {
                "url": url,
                "status": response.status,
                "response_data": data
            })

    except urllib.error.HTTPError as e:
        print(f"✗ HTTPError {e.code}: {e.reason}")

        # Read error response body for details
        try:
            error_body = e.read().decode()
            error_data = json.loads(error_body)
            print("Error details:")
            print(json.dumps(error_data, indent=2))

            logger.exception("Discord API HTTP error", {
                "url": url,
                "code": e.code,
                "reason": e.reason,
                "error_data": error_data
            })

            # Common Discord error codes
            if error_data.get("code") == 50001:
                print("→ Missing Access: Bot lacks permission to access this resource")
                logger.exception("Missing access permission", {"discord_error_code": 50001})
            elif error_data.get("code") == 50013:
                print("→ Missing Permissions: Bot lacks required permissions")
                logger.exception("Missing required permissions", {"discord_error_code": 50013})
            elif error_data.get("code") == 10003:
                print("→ Unknown Channel: Channel does not exist")
                logger.exception("Unknown channel", {"discord_error_code": 10003})
            elif error_data.get("code") == 10004:
                print("→ Unknown Guild: Guild does not exist")
                logger.exception("Unknown guild", {"discord_error_code": 10004})

        except (json.JSONDecodeError, UnicodeDecodeError):
            print("Could not parse error response body")
            logger.exception("Failed to parse error response", {"url": url})

    except (urllib.error.URLError, OSError, ValueError) as e:
        # Network errors, OS errors, or value errors
        print(f"✗ Error: {type(e).__name__}: {e}")
        logger.exception("API access error", {
            "url": url,
            "error_type": type(e).__name__,
            "error_message": str(e)
        })


def main() -> None:
    """Run Discord API access checks."""
    # Initialize logger
    logger = AstolfoLogger("discord_access_check")
    logger.info("Starting Discord API access check")

    token = os.getenv("DISCORD_TOKEN", "")
    channel_id = os.getenv("DISCORD_CHANNEL_ID", "")

    if not token:
        print("Error: DISCORD_TOKEN not set")
        logger.error("DISCORD_TOKEN not configured")
        return

    if not channel_id:
        print("Error: DISCORD_CHANNEL_ID not set")
        logger.error("DISCORD_CHANNEL_ID not configured")
        return

    logger.info("Configuration loaded", {
        "channel_id": channel_id,
        "has_token": bool(token)
    })

    print("Discord API Access Check")
    print("=" * 50)
    print(f"Channel ID: {channel_id}")
    print()

    # Test 1: Get channel info
    print("1. Checking channel access...")
    check_api_access(f"https://discord.com/api/v10/channels/{channel_id}", token, logger)
    print()

    # Test 2: List archived threads
    print("2. Checking archived threads access...")
    check_api_access(f"https://discord.com/api/v10/channels/{channel_id}/threads/archived/public", token, logger)
    print()

    # Test 3: Get bot user info
    print("3. Checking bot user...")
    check_api_access("https://discord.com/api/v10/users/@me", token, logger)
    print()

    # Test 4: Check specific thread if provided
    thread_id = "1391977832007208990"
    print(f"4. Checking specific thread: {thread_id}")
    check_api_access(f"https://discord.com/api/v10/channels/{thread_id}", token, logger)

    logger.info("Discord API access check completed")


if __name__ == "__main__":
    main()
