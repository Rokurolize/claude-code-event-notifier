#!/usr/bin/env python3
"""Test script specifically for Discord mention feature.

This script tests that Windows Discord notifications properly display
both the user mention and the notification message.

Usage:
    # Set your Discord user ID first
    export DISCORD_MENTION_USER_ID=YOUR_DISCORD_USER_ID
    python3 test_mentions.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def test_mention_notifications():
    """Test Discord notifications with user mentions."""
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"

    if not script_path.exists():
        print(f"Error: Notifier script not found at {script_path}")
        return False

    # Check if mention user ID is configured
    mention_user_id = os.environ.get("DISCORD_MENTION_USER_ID")
    if not mention_user_id:
        print("⚠️  DISCORD_MENTION_USER_ID not set!")
        print("Please set: export DISCORD_MENTION_USER_ID=YOUR_DISCORD_USER_ID")
        print("\nTo find your Discord User ID:")
        print(
            "1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)"
        )
        print("2. Right-click on your username in any channel")
        print("3. Select 'Copy User ID'")
        return False

    print(f"✓ Testing mentions for user ID: {mention_user_id}")
    print()

    # Test scenarios
    test_cases = [
        {
            "name": "Standard notification",
            "data": {
                "session_id": "mention-test-001",
                "message": "Standard test notification with mention",
            },
            "expected": f"<@{mention_user_id}> Standard test notification with mention",
        },
        {
            "name": "Short message",
            "data": {
                "session_id": "mention-test-002",
                "message": "Hi!",
            },
            "expected": f"<@{mention_user_id}> Hi!",
        },
        {
            "name": "Long message with emojis",
            "data": {
                "session_id": "mention-test-003",
                "message": "🎉 All tests passed! Build #1234 completed successfully. Coverage: 98.5%. Time: 2m 34s. Ready for production deployment! 🚀",
            },
            "expected": f"<@{mention_user_id}> 🎉 All tests passed! Build #1234 completed successfully. Coverage: 98.5%. Time: 2m 34s. Ready for production deployment! 🚀",
        },
        {
            "name": "Message with Discord formatting",
            "data": {
                "session_id": "mention-test-004",
                "message": "Check **PR #456** - `feat: add new feature` by @developer",
            },
            "expected": f"<@{mention_user_id}> Check **PR #456** - `feat: add new feature` by @developer",
        },
        {
            "name": "Empty message (should use default)",
            "data": {
                "session_id": "mention-test-005",
                # No message field
            },
            "expected": f"<@{mention_user_id}> System notification",
        },
        {
            "name": "Multi-line message",
            "data": {
                "session_id": "mention-test-006",
                "message": "Error detected:\nFile: main.py\nLine: 42\nDetails: Variable undefined",
            },
            "expected": f"<@{mention_user_id}> Error detected:\nFile: main.py\nLine: 42\nDetails: Variable undefined",
        },
    ]

    print(f"Running {len(test_cases)} mention tests...\n")

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test_case['name']}...", end="", flush=True)

        # Prepare event
        event = {"type": "Notification", "data": test_case["data"]}

        # Set environment
        env = os.environ.copy()
        env["CLAUDE_HOOK_EVENT"] = "Notification"
        env["DISCORD_DEBUG"] = "1"

        # Run the notifier
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                check=False,
                input=json.dumps(event["data"]).encode(),
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
            )

            if proc.returncode == 0:
                print(" ✓")
                expected_str = str(test_case["expected"])
                print(f"   Expected content: {expected_str[:50]}...")
            else:
                print(" ✗")
                print(f"   Error: {proc.stderr}")
        except subprocess.TimeoutExpired:
            print(" ✗ (timeout)")
        except Exception as e:
            print(f" ✗ ({e})")

        # Small delay between tests
        time.sleep(0.5)

    print("\n✅ Mention tests completed!")
    print("\n⚠️  IMPORTANT: Check your Discord to verify:")
    print("1. Windows notifications show both @mention and message")
    print("2. Discord channel shows proper formatting")
    print("3. You receive a notification sound/alert for each test")

    return True


def test_without_mention():
    """Test that notifications work without mention configuration."""
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"

    print("\nTesting notification WITHOUT mention...")

    # Remove mention config
    env = os.environ.copy()
    if "DISCORD_MENTION_USER_ID" in env:
        del env["DISCORD_MENTION_USER_ID"]

    env["CLAUDE_HOOK_EVENT"] = "Notification"
    env["DISCORD_DEBUG"] = "1"

    event_data = {
        "session_id": "no-mention-test",
        "message": "This should NOT have a mention",
    }

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            input=json.dumps(event_data).encode(),
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        if proc.returncode == 0:
            print("✓ Notification sent without mention")
        else:
            print(f"✗ Error: {proc.stderr}")
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    print("Discord Mention Feature Test")
    print("=" * 40)

    # Check Discord configuration
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    bot_token = os.environ.get("DISCORD_TOKEN")

    if not env_file.exists() and not webhook_url and not bot_token:
        print("⚠️  No Discord configuration found!")
        print(f"Please create {env_file} or set environment variables")
        sys.exit(1)

    # Run tests
    if test_mention_notifications():
        test_without_mention()

    print("\n✨ Testing complete!")
