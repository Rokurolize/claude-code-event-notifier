#!/usr/bin/env python3
"""Test script to verify Discord mentions work for Stop events."""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root and src directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from discord_notifier import EventTypes
from utils.astolfo_logger import setup_astolfo_logger

# Initialize logger for test execution
logger = setup_astolfo_logger(__name__)


def test_stop_event_with_mention():
    """Test Stop event with user mention configured."""
    logger.info(
        "test_start",
        context={
            "test_name": "test_stop_event_with_mention",
            "test_type": "feature",
            "event_type": EventTypes.STOP.value
        },
        astolfo_note="Starting Stop event mention test",
        ai_todo="Verify Discord mention functionality works for Stop events"
    )
    print("Testing Stop event with mention...")

    # Create test Stop event with secure temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_file:
        temp_path = temp_file.name
    
    logger.debug(
        "temp_file_created",
        context={
            "temp_path": temp_path,
            "file_suffix": ".txt"
        },
        ai_todo="Temporary file created for Stop event test"
    )

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
    
    logger.debug(
        "env_vars_set",
        context={
            "hook_event": EventTypes.STOP.value,
            "mention_user_id": "123456789012345678"
        },
        ai_todo="Environment variables configured for mention test"
    )

    # Create event JSON
    event_json = json.dumps(event_data)

    print(f"Event data: {event_json}")
    print("\nThis should send a Discord message with mention: <@123456789012345678> Session ended")
    print("\nNote: This test will only work if you have configured DISCORD_WEBHOOK_URL")
    
    logger.info(
        "test_setup_complete",
        context={
            "event_data_size": len(event_json),
            "expected_mention": "<@123456789012345678> Session ended",
            "tools_used": event_data["tools_used"],
            "messages_exchanged": event_data["messages_exchanged"],
            "duration": event_data["duration"]
        },
        human_note="Test setup completed. Discord webhook configuration required for actual sending.",
        ai_todo="Event data ready for Stop mention test"
    )

    # Note: We won't actually send the message in this test script
    # In real usage, the notifier reads from stdin
    
    logger.info(
        "test_complete",
        context={
            "test_name": "test_stop_event_with_mention",
            "status": "setup_only"
        },
        astolfo_note="Stop event mention test setup completed successfully"
    )


def test_notification_event_with_mention():
    """Test Notification event still works with mention."""
    logger.info(
        "test_start",
        context={
            "test_name": "test_notification_event_with_mention",
            "test_type": "feature",
            "event_type": EventTypes.NOTIFICATION.value
        },
        astolfo_note="Starting Notification event mention test",
        ai_todo="Verify Discord mention functionality works for Notification events"
    )
    print("\n\nTesting Notification event with mention...")

    # Create test Notification event
    event_data = {
        "hook_event_name": EventTypes.NOTIFICATION.value,
        "session_id": "test-session-456",
        "message": "Test notification message",
    }

    print(f"Event data: {json.dumps(event_data)}")
    print("\nThis should send a Discord message with mention: <@123456789012345678> Test notification message")
    
    logger.info(
        "notification_test_complete",
        context={
            "test_name": "test_notification_event_with_mention",
            "event_data": event_data,
            "expected_mention": "<@123456789012345678> Test notification message",
            "status": "setup_only"
        },
        astolfo_note="Notification event mention test setup completed successfully",
        ai_todo="Notification event data prepared for mention test"
    )


if __name__ == "__main__":
    logger.info(
        "test_suite_start",
        context={
            "test_suite": "Discord Mention Test Cases",
            "file": __file__,
            "total_tests": 2
        },
        astolfo_note="Starting Discord mention test suite for Stop and Notification events",
        ai_todo="Execute all mention tests and verify functionality"
    )
    
    print("Discord Mention Test Cases")
    print("=" * 50)
    
    try:
        test_stop_event_with_mention()
        test_notification_event_with_mention()
        
        logger.info(
            "test_suite_complete",
            context={
                "total_tests": 2,
                "status": "success"
            },
            astolfo_note="All Discord mention tests completed successfully",
            ai_todo="Review test results and proceed with integration testing if needed"
        )
        
    except Exception as e:
        logger.error(
            "test_suite_failed",
            exception=e,
            context={
                "test_suite": "Discord Mention Test Cases"
            },
            ai_todo="Check error details and fix any issues with mention tests"
        )
        raise

    print("\n\nTo actually test with Discord:")
    print("1. Configure your DISCORD_WEBHOOK_URL and DISCORD_MENTION_USER_ID")
    print("2. Run the integration test: python3 test.py")
    print("3. Or trigger real Claude Code Stop events")
    
    logger.info(
        "instructions_displayed",
        context={
            "next_steps": [
                "Configure DISCORD_WEBHOOK_URL and DISCORD_MENTION_USER_ID",
                "Run integration test",
                "Trigger real Claude Code Stop events"
            ]
        },
        human_note="Test completed. Instructions provided for actual Discord testing.",
        ai_todo="User should follow instructions for real Discord integration testing"
    )
