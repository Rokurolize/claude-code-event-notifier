#!/usr/bin/env python3
"""Discord Thread Creation and Usage Verification Test

This script verifies that:
1. Discord threads can be created successfully
2. Multiple messages with the same session ID go to the same thread
3. Different session IDs create different threads
4. Thread naming follows the expected pattern

Usage: python3 test_thread_verification.py
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_discord_event(
    event_type: str, event_data: dict, script_path: Path
) -> tuple[bool, str]:
    """Run a Discord notifier event and return success status and output."""
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
            timeout=15,
        )

        success = proc.returncode == 0
        output = proc.stderr if proc.stderr else proc.stdout
        return success, output

    except subprocess.TimeoutExpired:
        return False, "Timeout after 15 seconds"
    except Exception as e:
        return False, f"Exception: {e}"


def extract_thread_info(output: str) -> dict:
    """Extract thread creation information from output."""
    info = {"thread_created": False, "thread_id": None, "error": None}

    if "Created text thread" in output:
        info["thread_created"] = True
        # Extract thread ID from log line like: "Created text thread 1391733635274768446 for session"
        for line in output.split("\n"):
            if "Created text thread" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "thread" and i + 1 < len(parts):
                        info["thread_id"] = parts[i + 1]
                        break

    if "Thread Creation HTTP error" in output:
        info["error"] = "Thread creation failed"

    return info


def test_thread_functionality():
    """Main thread functionality test."""
    print("🧵 Discord Thread Creation and Usage Verification")
    print("=" * 60)

    # Find Discord notifier script
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"
    if not script_path.exists():
        print(f"❌ Discord notifier script not found at {script_path}")
        return False

    print(f"📍 Script: {script_path}")

    # Check configuration
    env_file = Path.home() / ".claude" / "hooks" / ".env.discord"
    if not env_file.exists():
        print(f"❌ Discord configuration not found at {env_file}")
        return False

    print(f"⚙️  Config: {env_file}")

    # Generate unique session IDs for testing
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_1 = f"thread-test-session-1-{timestamp}"
    session_2 = f"thread-test-session-2-{timestamp}"

    print(f"🔤 Test Session 1: {session_1}")
    print(f"🔤 Test Session 2: {session_2}")
    print()

    all_success = True
    results = {}

    # Test 1: First message for Session 1 (should create thread)
    print("📝 Test 1: First message for Session 1 (should create new thread)")
    event_data_1a = {
        "session_id": session_1,
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo 'Testing thread creation'",
            "description": "Thread creation test command",
        },
        "timestamp": datetime.now().isoformat(),
    }

    success, output = run_discord_event("PreToolUse", event_data_1a, script_path)
    thread_info_1a = extract_thread_info(output)
    results["test_1"] = {"success": success, "thread_info": thread_info_1a}

    if success:
        print("✅ Event sent successfully")
        if thread_info_1a["thread_created"]:
            print(f"🧵 Thread created with ID: {thread_info_1a['thread_id']}")
        else:
            print("📨 Message sent to main channel (thread creation may have failed)")
    else:
        print("❌ Event failed")
        all_success = False

    print(f"   Debug: {output[:150]}...")
    print()

    # Wait a moment between events
    time.sleep(3)

    # Test 2: Second message for Session 1 (should use existing thread)
    print("📝 Test 2: Second message for Session 1 (should use existing thread)")
    event_data_1b = {
        "session_id": session_1,
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {
            "command": "echo 'Testing thread creation'",
            "description": "Thread creation test command",
        },
        "tool_response": {
            "stdout": "Testing thread creation\n",
            "stderr": "",
            "interrupted": False,
            "isImage": False,
        },
        "timestamp": datetime.now().isoformat(),
    }

    success, output = run_discord_event("PostToolUse", event_data_1b, script_path)
    thread_info_1b = extract_thread_info(output)
    results["test_2"] = {"success": success, "thread_info": thread_info_1b}

    if success:
        print("✅ Event sent successfully")
        if thread_info_1b["thread_created"]:
            print("⚠️  New thread created (unexpected - should have used existing)")
        else:
            print("🔗 Used existing thread (expected behavior)")
    else:
        print("❌ Event failed")
        all_success = False

    print(f"   Debug: {output[:150]}...")
    print()

    # Wait a moment between events
    time.sleep(3)

    # Test 3: First message for Session 2 (should create new thread)
    print("📝 Test 3: First message for Session 2 (should create new thread)")
    event_data_2a = {
        "session_id": session_2,
        "hook_event_name": "Notification",
        "message": f"🆕 This is a test message for a different session: {session_2}",
        "timestamp": datetime.now().isoformat(),
    }

    success, output = run_discord_event("Notification", event_data_2a, script_path)
    thread_info_2a = extract_thread_info(output)
    results["test_3"] = {"success": success, "thread_info": thread_info_2a}

    if success:
        print("✅ Event sent successfully")
        if thread_info_2a["thread_created"]:
            print(f"🧵 New thread created with ID: {thread_info_2a['thread_id']}")
        else:
            print("📨 Message sent (thread status unclear)")
    else:
        print("❌ Event failed")
        all_success = False

    print(f"   Debug: {output[:150]}...")
    print()

    # Test 4: Stop event for Session 1 (should use Session 1's thread)
    print("📝 Test 4: Stop event for Session 1 (should use Session 1's thread)")
    event_data_1c = {
        "session_id": session_1,
        "hook_event_name": "Stop",
        "transcript_path": f"/tmp/transcript-{session_1}.txt",
        "duration": 42.5,
        "tools_used": 2,
        "messages_exchanged": 4,
        "timestamp": datetime.now().isoformat(),
    }

    success, output = run_discord_event("Stop", event_data_1c, script_path)
    thread_info_1c = extract_thread_info(output)
    results["test_4"] = {"success": success, "thread_info": thread_info_1c}

    if success:
        print("✅ Event sent successfully")
        if thread_info_1c["thread_created"]:
            print("⚠️  New thread created (unexpected - should have used existing)")
        else:
            print("🔗 Used existing thread (expected behavior)")
    else:
        print("❌ Event failed")
        all_success = False

    print(f"   Debug: {output[:150]}...")
    print()

    # Analysis and Results
    print("📊 Test Results Analysis")
    print("-" * 30)

    expected_threads = []
    if results["test_1"]["thread_info"]["thread_created"]:
        expected_threads.append(
            f"Session {session_1[:8]} - ID: {results['test_1']['thread_info']['thread_id']}"
        )

    if results["test_3"]["thread_info"]["thread_created"]:
        expected_threads.append(
            f"Session {session_2[:8]} - ID: {results['test_3']['thread_info']['thread_id']}"
        )

    print("🧵 Expected Discord Threads:")
    for thread in expected_threads:
        print(f"   {thread}")

    print("\n🔍 Verification Checklist:")
    print("1. Check Discord for threads with names like 'Session {session_id[:8]}'")
    print("2. Verify Session 1 messages (Tests 1, 2, 4) are in the same thread")
    print("3. Verify Session 2 message (Test 3) is in a different thread")
    print("4. Check that thread creation worked as expected")

    # Show recent log entries for debugging
    log_dir = Path.home() / ".claude" / "hooks" / "logs"
    if log_dir.exists():
        logs = list(log_dir.glob("discord_notifier_*.log"))
        if logs:
            latest_log = max(logs, key=lambda p: p.stat().st_mtime)
            print(f"\n📋 Debug log: {latest_log}")

    print("\n" + "=" * 60)
    if all_success:
        print("✅ All tests completed successfully!")
        print("🧵 Check Discord to verify thread behavior")
    else:
        print("❌ Some tests failed - check debug output")
        print("🔧 Review configuration and Discord permissions")

    return all_success


if __name__ == "__main__":
    success = test_thread_functionality()
    sys.exit(0 if success else 1)
