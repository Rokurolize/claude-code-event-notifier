#!/usr/bin/env python3
"""Thread Creation Test Script for Discord Notifier

This script specifically tests the thread creation functionality of the Discord notifier,
verifying that messages with the same session ID are grouped into the same Discord thread.

Usage: python3 test_thread_creation.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_notifier_event(
    event_type: str, event_data: dict, script_path: Path
) -> tuple[bool, str]:
    """Run the Discord notifier with a specific event."""
    env = os.environ.copy()
    env["CLAUDE_HOOK_EVENT"] = event_type
    env["DISCORD_DEBUG"] = "1"

    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            check=False,
            input=json.dumps(event_data),
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
        )

        success = proc.returncode == 0
        output = proc.stderr if proc.stderr else proc.stdout
        return success, output

    except subprocess.TimeoutExpired:
        return False, "Timeout after 10 seconds"
    except Exception as e:
        return False, f"Exception: {e}"


def test_thread_creation():
    """Test Discord thread creation functionality."""
    print("🧵 Discord Thread Creation Test")
    print("=" * 50)

    # Find the Discord notifier script
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"
    if not script_path.exists():
        print(f"❌ Error: Discord notifier script not found at {script_path}")
        return False

    print(f"📍 Script: {script_path}")

    # Check configuration
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    if not env_file.exists():
        print(f"❌ Error: Discord configuration not found at {env_file}")
        return False

    print(f"⚙️  Config: {env_file}")

    # Generate unique session ID for this test
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_id = f"context7-thread-test-{timestamp}"
    print(f"🔤 Session ID: {session_id}")

    # Create test events for the same session
    test_events = [
        {
            "type": "PreToolUse",
            "data": {
                "session_id": session_id,
                "hook_event_name": "PreToolUse",
                "tool_name": "Task",
                "tool_input": {
                    "description": "Context7 thread creation test",
                    "prompt": "Testing Discord thread creation functionality with Context7",
                },
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "type": "PostToolUse",
            "data": {
                "session_id": session_id,
                "hook_event_name": "PostToolUse",
                "tool_name": "Task",
                "tool_input": {
                    "description": "Context7 thread creation test",
                    "prompt": "Testing Discord thread creation functionality with Context7",
                },
                "tool_response": "Thread creation test completed successfully. This message should appear in the same Discord thread as the previous PreToolUse event.",
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "type": "Notification",
            "data": {
                "session_id": session_id,
                "hook_event_name": "Notification",
                "message": "🧵 Thread creation verification: This notification should appear in the same thread as the previous events.",
                "timestamp": datetime.now().isoformat(),
            },
        },
        {
            "type": "Stop",
            "data": {
                "session_id": session_id,
                "hook_event_name": "Stop",
                "transcript_path": f"/tmp/transcript-{session_id}.txt",
                "duration": 45.2,
                "tools_used": 3,
                "messages_exchanged": 8,
                "timestamp": datetime.now().isoformat(),
            },
        },
    ]

    print(f"\n🚀 Running {len(test_events)} test events...")
    print("📝 Events should all appear in the same Discord thread")
    print()

    all_success = True

    for i, event in enumerate(test_events, 1):
        event_type = event["type"]
        print(
            f"[{i}/{len(test_events)}] Sending {event_type} event...",
            end="",
            flush=True,
        )

        success, output = run_notifier_event(event_type, event["data"], script_path)

        if success:
            print(" ✅")
            if "Thread" in output or "thread" in output:
                print(
                    f"    💬 Thread info: {output.split('Thread')[0]}Thread{output.split('Thread')[1].split(chr(10))[0]}"
                )
        else:
            print(" ❌")
            print(f"    🔍 Debug: {output[:100]}...")
            all_success = False

        # Small delay between events to see them arrive sequentially
        if i < len(test_events):
            time.sleep(2)

    print()

    # Test a second session to verify different threads are created
    print("🔄 Testing second session (should create new thread)...")
    second_session_id = f"context7-thread-test-2-{timestamp}"

    second_event = {
        "type": "Notification",
        "data": {
            "session_id": second_session_id,
            "hook_event_name": "Notification",
            "message": f"🆕 New session test: This should appear in a DIFFERENT thread than the previous messages (session: {second_session_id})",
            "timestamp": datetime.now().isoformat(),
        },
    }

    success, output = run_notifier_event(
        "Notification", second_event["data"], script_path
    )

    if success:
        print("✅ Second session event sent successfully")
    else:
        print(f"❌ Second session event failed: {output[:100]}...")
        all_success = False

    print()
    print("🔍 Verification Steps:")
    print("1. Check your Discord channel for messages")
    print("2. Verify that events 1-4 appear in the same thread")
    print("3. Verify that the second session event appears in a different thread")
    print("4. Thread names should follow pattern: 'Context7Test {session_id[:8]}'")

    expected_thread_names = [
        f"Context7Test {session_id[:8]}",
        f"Context7Test {second_session_id[:8]}",
    ]

    print("5. Expected thread names:")
    for name in expected_thread_names:
        print(f"   - {name}")

    # Show log location for debugging
    log_dir = Path.home() / ".claude" / "hooks" / "logs"
    if log_dir.exists():
        logs = list(log_dir.glob("discord_notifier_*.log"))
        if logs:
            latest_log = max(logs, key=lambda p: p.stat().st_mtime)
            print(f"\n📋 Debug log: {latest_log}")

    print()
    if all_success:
        print("✅ All events sent successfully!")
        print(
            "🧵 Thread creation test completed. Check Discord to verify threading behavior."
        )
    else:
        print("❌ Some events failed. Check the debug output above.")

    return all_success


def test_configuration_validation():
    """Test the thread configuration validation."""
    print("\n⚙️  Configuration Validation Test")
    print("-" * 30)

    # Test with current config
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"

    # Create a minimal test event to trigger config validation
    test_event = {
        "session_id": "config-test",
        "hook_event_name": "Notification",
        "message": "Configuration test message",
    }

    print("Testing current configuration...", end="", flush=True)
    success, output = run_notifier_event("Notification", test_event, script_path)

    if success:
        print(" ✅")
        print("✅ Configuration validation passed")
    else:
        print(" ❌")
        print(f"❌ Configuration issue: {output}")
        return False

    return True


if __name__ == "__main__":
    print("Discord Notifier Thread Creation Test Suite")
    print("=" * 60)

    # Run configuration validation first
    config_ok = test_configuration_validation()

    if not config_ok:
        print("\n❌ Configuration validation failed. Please check your Discord setup.")
        sys.exit(1)

    # Run thread creation tests
    print("\n" + "=" * 60)
    success = test_thread_creation()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Thread creation test completed successfully!")
        print("📱 Check your Discord to verify threading behavior.")
    else:
        print("💥 Thread creation test encountered issues.")
        print("🔧 Check the debug output and logs for details.")

    sys.exit(0 if success else 1)
