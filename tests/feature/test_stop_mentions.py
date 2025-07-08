#!/usr/bin/env python3
"""Test script to verify Discord mentions work for Stop events."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from discord_notifier import EventTypes


def test_stop_event_with_mention():
    """Test Stop event with user mention configured."""
    print("Testing Stop event with mention...")

    # Create test Stop event with secure temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
        temp_path = temp_file.name

    event_data = {
        "hook_event_name": EventTypes.STOP.value,
        "session_id": "test-session-123",
        "transcript_path": temp_path,
        "duration": 300,
        "tools_used": 5,
        "messages_exchanged": 10,
    }

    # Set environment variables
    os.environ["CLAUDE_HOOK_EVENT"] = EventTypes.STOP.value
    os.environ["DISCORD_MENTION_USER_ID"] = "123456789012345678"  # Test user ID

    # Create event JSON
    event_json = json.dumps(event_data)

    print(f"Event data: {event_json}")
    print("\nThis should send a Discord message with mention: <@123456789012345678> Session ended")
    print("\nNote: This test will only work if you have configured DISCORD_WEBHOOK_URL")

    # Note: We won't actually send the message in this test script
    # In real usage, the notifier reads from stdin


def test_notification_event_with_mention():
    """Test Notification event still works with mention."""
    print("\n\nTesting Notification event with mention...")

    # Create test Notification event
    event_data = {
        "hook_event_name": EventTypes.NOTIFICATION.value,
        "session_id": "test-session-456",
        "message": "Test notification message",
    }

    print(f"Event data: {json.dumps(event_data)}")
    print("\nThis should send a Discord message with mention: <@123456789012345678> Test notification message")


if __name__ == "__main__":
    print("Discord Mention Test Cases")
    print("=" * 50)

    test_stop_event_with_mention()
    test_notification_event_with_mention()

    print("\n\nTo actually test with Discord:")
    print("1. Configure your DISCORD_WEBHOOK_URL and DISCORD_MENTION_USER_ID")
    print("2. Run the integration test: python3 test.py")
    print("3. Or trigger real Claude Code Stop events")
