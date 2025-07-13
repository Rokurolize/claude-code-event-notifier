#!/usr/bin/env python3
"""Test script for the simplified Discord notifier.

Usage: python3 test.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.astolfo_logger import AstolfoLogger


def test_notifier():
    """Test the Discord notifier with sample events."""
    # Initialize structured logging
    logger = AstolfoLogger("integration_test")
    
    # Always use the main discord_notifier.py from the src directory
    script_path = Path(__file__).parent.parent.parent / "src" / "discord_notifier.py"

    if not script_path.exists():
        print(f"Error: Notifier script not found at {script_path}")
        return False

    # Test events
    test_events = [
        {
            "type": "PreToolUse",
            "data": {
                "session_id": "test-session-123",
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la /home/user/projects"},
            },
        },
        {
            "type": "PostToolUse",
            "data": {
                "session_id": "test-session-123",
                "tool_name": "Bash",
                "execution_time": 0.25,
                "tool_input": {"command": "echo 'Hello World'"},
                "tool_response": {
                    "stdout": "Hello World\n",
                    "stderr": "",
                    "exit_code": 0,
                },
            },
        },
        {
            "type": "Notification",
            "data": {
                "session_id": "test-session-123",
                "message": "This is a test notification from the simplified notifier",
            },
        },
        # Additional notification tests for mention feature
        {
            "type": "Notification",
            "data": {
                "session_id": "test-mention-short",
                "message": "Quick test",
            },
        },
        {
            "type": "Notification",
            "data": {
                "session_id": "test-mention-long",
                "message": "🚀 Build completed successfully! All tests passed (42/42). Ready for deployment. This is a longer notification message to test how it appears in Windows Discord notifications.",
            },
        },
        {
            "type": "Notification",
            "data": {
                "session_id": "test-mention-special",
                "message": "Test @here with #channel mentions and special chars: <>&\"'",
            },
        },
        {
            "type": "Notification",
            "data": {
                "session_id": "test-mention-empty",
                # Missing message - should use default "System notification"
            },
        },
        {"type": "Stop", "data": {"session_id": "test-session-123"}},
        {
            "type": "SubagentStop",
            "data": {
                "session_id": "test-session-123",
                "subagent_id": "subagent-456",
                "result": "Task completed successfully",
            },
        },
    ]

    print("Testing Discord Notifier...")
    print(f"Script: {script_path}")
    print()
    
    # Log test start with structured data
    logger.info("Integration test started", {
        "script_path": str(script_path),
        "total_events": len(test_events),
        "test_timestamp": time.time()
    })

    # Check configuration
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    bot_token = os.environ.get("DISCORD_TOKEN")

    if not env_file.exists() and not webhook_url and not bot_token:
        print("⚠️  No Discord configuration found!")
        print(f"Please create {env_file} or set environment variables")
        logger.warning("Discord configuration missing", {
            "env_file_path": str(env_file),
            "has_webhook_url": bool(webhook_url),
            "has_bot_token": bool(bot_token)
        })
        return False

    print("✓ Discord configuration found")
    print()
    logger.info("Discord configuration validated", {
        "config_source": "env_file" if env_file.exists() else "environment_variables"
    })

    # Test each event
    test_results = []
    for i, event in enumerate(test_events, 1):
        test_start_time = time.time()
        print(f"Test {i}/{len(test_events)}: {event['type']} event...", end="", flush=True)
        
        # Log individual test start
        logger.info("Test event started", {
            "test_number": i,
            "event_type": event['type'],
            "session_id": event['data'].get('session_id', 'unknown'),
            "start_time": test_start_time
        })

        # Set event type in environment
        env = os.environ.copy()
        env["CLAUDE_HOOK_EVENT"] = str(event["type"])
        env["DISCORD_DEBUG"] = "1"  # Enable debug for testing

        # Run the notifier
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                check=False,
                input=json.dumps(event["data"]),
                text=True,
                capture_output=True,
                env=env,
                timeout=5,
            )

            test_duration = time.time() - test_start_time
            if proc.returncode == 0:
                print(" ✓")
                if proc.stderr:
                    print(f"  Debug output: {proc.stderr.strip()[:100]}...")
                
                # Log successful test
                logger.info("Test event completed successfully", {
                    "test_number": i,
                    "event_type": event['type'],
                    "duration_seconds": round(test_duration, 3),
                    "has_debug_output": bool(proc.stderr)
                })
                test_results.append("success")
            else:
                print(" ✗")
                print(f"  Error: Exit code {proc.returncode}")
                if proc.stderr:
                    print(f"  stderr: {proc.stderr}")
                
                # Log failed test
                logger.error("Test event failed", {
                    "test_number": i,
                    "event_type": event['type'],
                    "exit_code": proc.returncode,
                    "duration_seconds": round(test_duration, 3),
                    "error_output": proc.stderr[:500] if proc.stderr else None
                })
                test_results.append("failed")

        except subprocess.TimeoutExpired:
            test_duration = time.time() - test_start_time
            print(" ✗ (timeout)")
            logger.error("Test event timed out", {
                "test_number": i,
                "event_type": event['type'],
                "duration_seconds": round(test_duration, 3),
                "timeout_limit": 5
            })
            test_results.append("timeout")
        except Exception as e:
            test_duration = time.time() - test_start_time
            print(f" ✗ ({e})")
            logger.error("Test event exception", {
                "test_number": i,
                "event_type": event['type'],
                "duration_seconds": round(test_duration, 3),
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            })
            test_results.append("exception")

    print("\nTest complete!")
    print("\nCheck your Discord channel for the test messages.")
    
    # Log final test summary
    success_count = test_results.count("success")
    total_count = len(test_results)
    logger.info("Integration test completed", {
        "total_tests": total_count,
        "successful_tests": success_count,
        "failed_tests": test_results.count("failed"),
        "timeout_tests": test_results.count("timeout"),
        "exception_tests": test_results.count("exception"),
        "success_rate": round(success_count / total_count * 100, 1) if total_count > 0 else 0,
        "test_results": test_results
    })

    # Show log location
    log_dir = Path.home() / ".claude" / "hooks" / "logs"
    if log_dir.exists():
        logs = list(log_dir.glob("discord_notifier_*.log"))
        if logs:
            latest_log = max(logs, key=lambda p: p.stat().st_mtime)
            print(f"\nDebug log: {latest_log}")

    return True


if __name__ == "__main__":
    success = test_notifier()
    sys.exit(0 if success else 1)
