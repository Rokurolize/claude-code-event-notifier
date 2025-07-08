#!/usr/bin/env python3
"""Check Discord API access and permissions."""

import json
import os
import urllib.error
import urllib.request


def check_api_access(url: str, token: str) -> None:
    """Check Discord API access with detailed error reporting.

    Args:
        url: Discord API URL to test
        token: Bot token for authentication
    """
    print(f"Testing: {url}")

    try:
        headers = {"Authorization": f"Bot {token}"}
        request = urllib.request.Request(url, headers=headers)  # noqa: S310

        with urllib.request.urlopen(request) as response:  # type: ignore[misc] # noqa: S310
            print(f"✓ Success: {response.status}")
            data = json.loads(response.read().decode())
            print(f"Response: {json.dumps(data, indent=2)}")

    except urllib.error.HTTPError as e:
        print(f"✗ HTTPError {e.code}: {e.reason}")

        # Read error response body for details
        try:
            error_body = e.read().decode()
            error_data = json.loads(error_body)
            print("Error details:")
            print(json.dumps(error_data, indent=2))

            # Common Discord error codes
            if error_data.get("code") == 50001:
                print("→ Missing Access: Bot lacks permission to access this resource")
            elif error_data.get("code") == 50013:
                print("→ Missing Permissions: Bot lacks required permissions")
            elif error_data.get("code") == 10003:
                print("→ Unknown Channel: Channel does not exist")
            elif error_data.get("code") == 10004:
                print("→ Unknown Guild: Guild does not exist")

        except Exception:
            print("Could not parse error response body")

    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")


def main() -> None:
    """Run Discord API access checks."""
    token = os.getenv("DISCORD_TOKEN", "")
    channel_id = os.getenv("DISCORD_CHANNEL_ID", "")

    if not token:
        print("Error: DISCORD_TOKEN not set")
        return

    if not channel_id:
        print("Error: DISCORD_CHANNEL_ID not set")
        return

    print("Discord API Access Check")
    print("=" * 50)
    print(f"Channel ID: {channel_id}")
    print()

    # Test 1: Get channel info
    print("1. Checking channel access...")
    check_api_access(f"https://discord.com/api/v10/channels/{channel_id}", token)
    print()

    # Test 2: List archived threads
    print("2. Checking archived threads access...")
    check_api_access(f"https://discord.com/api/v10/channels/{channel_id}/threads/archived/public", token)
    print()

    # Test 3: Get bot user info
    print("3. Checking bot user...")
    check_api_access("https://discord.com/api/v10/users/@me", token)
    print()

    # Test 4: Check specific thread if provided
    thread_id = "1391977832007208990"
    print(f"4. Checking specific thread: {thread_id}")
    check_api_access(f"https://discord.com/api/v10/channels/{thread_id}", token)


if __name__ == "__main__":
    main()
