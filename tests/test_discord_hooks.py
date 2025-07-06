#!/usr/bin/env python3
"""
Test Discord Hooks Integration

This script tests the Discord event logger by simulating different
Claude Code hook events and sending them to Discord.

Usage: python3 test_discord_hooks.py [--webhook-url URL]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def create_test_hook_data(event_type):
    """Create test hook data for different event types."""
    base_data = {
        "session_id": "test123456",
        "transcript_path": "/tmp/test_conversation.jsonl",
    }

    if event_type == "PreToolUse":
        return {
            **base_data,
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/home/user/test.py",
                "content": "print('Hello, World!')\n# This is a test file\n",
            },
        }

    elif event_type == "PostToolUse":
        return {
            **base_data,
            "tool_name": "Write",
            "tool_input": {"file_path": "/home/user/test.py"},
            "execution_time": 0.42,
        }

    elif event_type == "Notification":
        return {
            **base_data,
            "message": "Test notification from Claude Code hooks system",
        }

    elif event_type == "Stop":
        return {**base_data, "duration": 180.5}

    elif event_type == "SubagentStop":
        return {**base_data, "subagent_task": "analyze_code"}

    return base_data


def test_event(event_type, webhook_url=None):
    """Test a specific event type."""
    print(f"Testing {event_type} event...")

    # Create test data
    test_data = create_test_hook_data(event_type)

    # Set up environment
    env = {}
    env["CLAUDE_HOOK_EVENT"] = event_type

    if webhook_url:
        env["DISCORD_WEBHOOK_URL"] = webhook_url

    # Get script path
    script_path = Path(__file__).parent / "discord_event_logger.py"

    if not script_path.exists():
        print(f"Error: Discord event logger not found at {script_path}")
        return False

    try:
        # Run the Discord logger script
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**dict(os.environ), **env},
        )

        # Send test data
        stdout, stderr = process.communicate(input=json.dumps(test_data))

        if process.returncode == 0:
            print(f"  ✅ {event_type} event sent successfully")
            if stdout:
                print(f"  Output: {stdout.strip()}")
            return True
        else:
            print(f"  ❌ {event_type} event failed")
            if stderr:
                print(f"  Error: {stderr.strip()}")
            return False

    except Exception as e:
        print(f"  ❌ Error testing {event_type}: {e}")
        return False


def main():
    """Main test function."""

    parser = argparse.ArgumentParser(description="Test Discord hooks integration")
    parser.add_argument("--webhook-url", help="Discord webhook URL for testing")
    parser.add_argument(
        "--event",
        choices=["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"],
        help="Test specific event type",
    )

    args = parser.parse_args()

    print("Discord Hooks Integration Test")
    print("=" * 30)

    # Check configuration
    config_found = False
    if args.webhook_url:
        print(f"Using webhook URL: {args.webhook_url[:30]}...")
        config_found = True
    elif os.environ.get("DISCORD_WEBHOOK_URL"):
        print("Using DISCORD_WEBHOOK_URL from environment")
        config_found = True
    elif os.environ.get("DISCORD_TOKEN") and os.environ.get("DISCORD_CHANNEL_ID"):
        print("Using Discord bot token from environment")
        config_found = True
    else:
        # Check .env.test file
        env_file = Path(__file__).parent / ".env.test"
        if env_file.exists():
            print(f"Using Discord config from {env_file}")
            config_found = True

    if not config_found:
        print("❌ No Discord configuration found!")
        print("Please provide one of:")
        print("  - --webhook-url argument")
        print("  - DISCORD_WEBHOOK_URL environment variable")
        print("  - DISCORD_TOKEN and DISCORD_CHANNEL_ID environment variables")
        print("  - .env.test file with Discord credentials")
        sys.exit(1)

    print()

    # Test events
    if args.event:
        events_to_test = [args.event]
    else:
        events_to_test = [
            "PreToolUse",
            "PostToolUse",
            "Notification",
            "Stop",
            "SubagentStop",
        ]

    success_count = 0
    total_count = len(events_to_test)

    for event in events_to_test:
        if test_event(event, args.webhook_url):
            success_count += 1
        time.sleep(1)  # Small delay between tests

    print()
    print(f"Test Results: {success_count}/{total_count} events sent successfully")

    if success_count == total_count:
        print("🎉 All tests passed! Discord hooks are working correctly.")
        print()
        print("Next steps:")
        print("1. Run: python3 setup_discord_hooks.py")
        print("2. Discord notifications will appear for all Claude Code events")
    else:
        print("⚠️  Some tests failed. Check your Discord configuration.")
        sys.exit(1)


if __name__ == "__main__":
    main()
