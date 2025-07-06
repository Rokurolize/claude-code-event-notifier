#!/usr/bin/env python3
"""
Test script for the simplified Discord notifier.

Usage: python3 test_simple.py
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_notifier():
    """Test the Discord notifier with sample events."""
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"

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
            },
        },
        {
            "type": "Notification",
            "data": {
                "session_id": "test-session-123",
                "message": "This is a test notification from the simplified notifier",
            },
        },
        {"type": "Stop", "data": {"session_id": "test-session-123"}},
    ]

    print("Testing Discord Notifier...")
    print(f"Script: {script_path}")
    print()

    # Check configuration
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    bot_token = os.environ.get("DISCORD_TOKEN")

    if not env_file.exists() and not webhook_url and not bot_token:
        print("⚠️  No Discord configuration found!")
        print(f"Please create {env_file} or set environment variables")
        return False

    print("✓ Discord configuration found")
    print()

    # Test each event
    for i, event in enumerate(test_events, 1):
        print(
            f"Test {i}/{len(test_events)}: {event['type']} event...", end="", flush=True
        )

        # Set event type in environment
        env = os.environ.copy()
        env["CLAUDE_HOOK_EVENT"] = event["type"]
        env["DISCORD_DEBUG"] = "1"  # Enable debug for testing

        # Run the notifier
        try:
            proc = subprocess.run(
                [sys.executable, str(script_path)],
                input=json.dumps(event["data"]),
                text=True,
                capture_output=True,
                env=env,
                timeout=5,
            )

            if proc.returncode == 0:
                print(" ✓")
                if proc.stderr:
                    print(f"  Debug output: {proc.stderr.strip()[:100]}...")
            else:
                print(" ✗")
                print(f"  Error: Exit code {proc.returncode}")
                if proc.stderr:
                    print(f"  stderr: {proc.stderr}")

        except subprocess.TimeoutExpired:
            print(" ✗ (timeout)")
        except Exception as e:
            print(f" ✗ ({e})")

    print("\nTest complete!")
    print("\nCheck your Discord channel for the test messages.")

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
