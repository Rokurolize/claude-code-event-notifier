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

# Add project root and src directory to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from utils.astolfo_logger import setup_astolfo_logger

# Initialize logger for test execution
logger = setup_astolfo_logger(__name__)


def test_mention_notifications() -> bool:
    """Test Discord notifications with user mentions."""
    logger.info(
        "test_start",
        context={
            "test_function": "test_mention_notifications",
            "test_type": "mention_integration",
            "total_test_cases": 6
        },
        astolfo_note="Starting comprehensive Discord mention notification tests",
        ai_todo="Execute all test cases and verify mention functionality"
    )
    
    script_path = Path(__file__).parent.parent.parent / "src" / "discord_notifier.py"

    if not script_path.exists():
        error_msg = f"Notifier script not found at {script_path}"
        print(f"Error: {error_msg}")
        logger.error(
            "script_not_found",
            context={
                "expected_path": str(script_path),
                "exists": script_path.exists()
            },
            ai_todo="Check discord_notifier.py location and fix path reference"
        )
        return False

    # Check if mention user ID is configured
    mention_user_id = os.environ.get("DISCORD_MENTION_USER_ID")
    if not mention_user_id:
        error_msg = "DISCORD_MENTION_USER_ID not configured"
        print("⚠️  DISCORD_MENTION_USER_ID not set!")
        print("Please set: export DISCORD_MENTION_USER_ID=YOUR_DISCORD_USER_ID")
        print("\nTo find your Discord User ID:")
        print("1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)")
        print("2. Right-click on your username in any channel")
        print("3. Select 'Copy User ID'")
        
        logger.error(
            "mention_user_id_missing",
            context={
                "env_var": "DISCORD_MENTION_USER_ID",
                "required": True
            },
            human_note="User needs to configure Discord User ID for mention testing",
            ai_todo="Guide user through Discord User ID setup process"
        )
        return False

    print(f"✓ Testing mentions for user ID: {mention_user_id}")
    print()
    
    logger.info(
        "mention_config_found",
        context={
            "mention_user_id": mention_user_id,
            "script_path": str(script_path)
        },
        astolfo_note="Discord mention configuration validated successfully",
        ai_todo="Proceed with mention test execution"
    )

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
                "message": (
                    "🎉 All tests passed! Build #1234 completed successfully. "
                    "Coverage: 98.5%. Time: 2m 34s. Ready for production deployment! 🚀"
                ),
            },
            "expected": (
                f"<@{mention_user_id}> 🎉 All tests passed! Build #1234 completed successfully. "
                f"Coverage: 98.5%. Time: 2m 34s. Ready for production deployment! 🚀"
            ),
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
    
    logger.info(
        "test_cases_start",
        context={
            "total_test_cases": len(test_cases),
            "test_case_names": [tc["name"] for tc in test_cases]
        },
        astolfo_note="Starting execution of all mention test cases",
        ai_todo="Execute each test case and log subprocess results"
    )

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test_case['name']}...", end="", flush=True)
        
        logger.debug(
            "test_case_start",
            context={
                "test_index": i,
                "test_name": test_case["name"],
                "session_id": test_case["data"].get("session_id", "unknown"),
                "message_length": len(test_case["data"].get("message", ""))
            },
            ai_todo=f"Execute test case {i}: {test_case['name']}"
        )

        # Prepare event
        event = {"type": "Notification", "data": test_case["data"]}

        # Set environment
        env = os.environ.copy()
        env["CLAUDE_HOOK_EVENT"] = "Notification"
        env["DISCORD_DEBUG"] = "1"

        # Run the notifier
        try:
            logger.debug(
                "subprocess_start",
                context={
                    "command": [sys.executable, str(script_path)],
                    "env_vars": {
                        "CLAUDE_HOOK_EVENT": env.get("CLAUDE_HOOK_EVENT"),
                        "DISCORD_DEBUG": env.get("DISCORD_DEBUG"),
                        "DISCORD_MENTION_USER_ID": "***" if env.get("DISCORD_MENTION_USER_ID") else None
                    },
                    "input_size": len(json.dumps(event["data"]))
                },
                ai_todo="Execute discord_notifier.py subprocess"
            )
            
            proc: subprocess.CompletedProcess[str] = subprocess.run(
                [sys.executable, str(script_path)],
                check=False,
                input=json.dumps(event["data"]),
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
            )

            if proc.returncode == 0:
                print(" ✓")
                expected_str = str(test_case["expected"])
                print(f"   Expected content: {expected_str[:50]}...")
                
                logger.info(
                    "test_case_success",
                    context={
                        "test_name": test_case["name"],
                        "return_code": proc.returncode,
                        "stdout_length": len(proc.stdout),
                        "stderr_length": len(proc.stderr),
                        "expected_content": expected_str[:100]
                    },
                    astolfo_note=f"Test case '{test_case['name']}' executed successfully",
                    ai_todo="Verify Discord message was sent with correct mention"
                )
            else:
                print(" ✗")
                print(f"   Error: {proc.stderr}")
                
                logger.error(
                    "test_case_failed",
                    context={
                        "test_name": test_case["name"],
                        "return_code": proc.returncode,
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                        "command": [sys.executable, str(script_path)]
                    },
                    ai_todo=f"Investigate failure in test case: {test_case['name']}"
                )
        except subprocess.TimeoutExpired:
            print(" ✗ (timeout)")
            logger.error(
                "test_case_timeout",
                context={
                    "test_name": test_case["name"],
                    "timeout_seconds": 10
                },
                ai_todo="Check for hanging processes or network issues"
            )
        except (OSError, ValueError) as e:
            print(f" ✗ ({e})")
            logger.error(
                "test_case_exception",
                exception=e,
                context={
                    "test_name": test_case["name"],
                    "exception_type": type(e).__name__
                },
                ai_todo="Check system environment and subprocess execution"
            )

        # Small delay between tests
        time.sleep(0.5)

    print("\n✅ Mention tests completed!")
    print("\n⚠️  IMPORTANT: Check your Discord to verify:")
    print("1. Windows notifications show both @mention and message")
    print("2. Discord channel shows proper formatting")
    print("3. You receive a notification sound/alert for each test")
    
    logger.info(
        "test_suite_complete",
        context={
            "total_tests": len(test_cases),
            "test_function": "test_mention_notifications"
        },
        human_note="All mention tests completed. User should verify Discord notifications manually.",
        astolfo_note="Mention notification test suite completed successfully",
        ai_todo="User should check Discord for actual mention notifications"
    )

    return True


def test_without_mention() -> None:
    """Test that notifications work without mention configuration."""
    logger.info(
        "test_start",
        context={
            "test_function": "test_without_mention",
            "test_type": "no_mention_test"
        },
        astolfo_note="Starting test for notifications without mention configuration",
        ai_todo="Verify notifications work correctly without DISCORD_MENTION_USER_ID"
    )
    
    script_path = Path(__file__).parent.parent.parent / "src" / "discord_notifier.py"

    print("\nTesting notification WITHOUT mention...")

    # Remove mention config
    env = os.environ.copy()
    had_mention_id = "DISCORD_MENTION_USER_ID" in env
    if "DISCORD_MENTION_USER_ID" in env:
        del env["DISCORD_MENTION_USER_ID"]

    env["CLAUDE_HOOK_EVENT"] = "Notification"
    env["DISCORD_DEBUG"] = "1"
    
    logger.debug(
        "env_setup_no_mention",
        context={
            "had_mention_id": had_mention_id,
            "hook_event": "Notification",
            "debug_enabled": True
        },
        ai_todo="Execute notification test without mention configuration"
    )

    event_data = {
        "session_id": "no-mention-test",
        "message": "This should NOT have a mention",
    }

    try:
        logger.debug(
            "subprocess_start_no_mention",
            context={
                "command": [sys.executable, str(script_path)],
                "event_data": event_data,
                "input_size": len(json.dumps(event_data))
            },
            ai_todo="Execute subprocess without mention configuration"
        )
        
        proc: subprocess.CompletedProcess[str] = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            input=json.dumps(event_data),
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

        if proc.returncode == 0:
            print("✓ Notification sent without mention")
            logger.info(
                "no_mention_test_success",
                context={
                    "return_code": proc.returncode,
                    "stdout_length": len(proc.stdout),
                    "stderr_length": len(proc.stderr)
                },
                astolfo_note="Notification sent successfully without mention configuration",
                ai_todo="Verify notification appears in Discord without @mention"
            )
        else:
            print(f"✗ Error: {proc.stderr}")
            logger.error(
                "no_mention_test_failed",
                context={
                    "return_code": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr
                },
                ai_todo="Investigate why notification failed without mention"
            )
    except (OSError, ValueError, subprocess.TimeoutExpired) as e:
        print(f"✗ Error: {e}")
        logger.error(
            "no_mention_test_exception",
            exception=e,
            context={
                "exception_type": type(e).__name__
            },
            ai_todo="Check subprocess execution environment"
        )


if __name__ == "__main__":
    logger.info(
        "test_suite_start",
        context={
            "test_suite": "Discord Mention Feature Test",
            "file": __file__
        },
        astolfo_note="Starting comprehensive Discord mention feature test suite",
        ai_todo="Validate Discord configuration and execute all tests"
    )
    
    print("Discord Mention Feature Test")
    print("=" * 40)

    # Check Discord configuration
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    bot_token = os.environ.get("DISCORD_TOKEN")
    
    logger.debug(
        "discord_config_check",
        context={
            "env_file_exists": env_file.exists(),
            "webhook_url_set": bool(webhook_url),
            "bot_token_set": bool(bot_token),
            "env_file_path": str(env_file)
        },
        ai_todo="Validate Discord configuration before running tests"
    )

    if not env_file.exists() and not webhook_url and not bot_token:
        error_msg = "No Discord configuration found"
        print("⚠️  No Discord configuration found!")
        print(f"Please create {env_file} or set environment variables")
        
        logger.error(
            "discord_config_missing",
            context={
                "env_file": str(env_file),
                "env_file_exists": env_file.exists(),
                "webhook_url_set": bool(webhook_url),
                "bot_token_set": bool(bot_token)
            },
            human_note="User needs to configure Discord webhook or bot token",
            ai_todo="Guide user through Discord configuration setup"
        )
        sys.exit(1)

    # Run tests
    try:
        if test_mention_notifications():
            test_without_mention()
        
        logger.info(
            "all_tests_complete",
            context={
                "test_suite": "Discord Mention Feature Test",
                "status": "success"
            },
            astolfo_note="All Discord mention tests completed successfully",
            ai_todo="User should verify Discord notifications manually"
        )
        
    except Exception as e:
        logger.error(
            "test_suite_failed",
            exception=e,
            context={
                "test_suite": "Discord Mention Feature Test"
            },
            ai_todo="Debug test suite failure and fix issues"
        )
        raise

    print("\n✨ Testing complete!")
