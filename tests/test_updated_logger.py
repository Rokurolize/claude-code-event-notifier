#!/usr/bin/env python3
"""Test the updated discord_event_logger.py with proper headers."""

import json
import subprocess
import sys
import os

# Test data simulating a Claude Code hook event
test_event = {
    "session_id": "test-session-123",
    "tool_name": "Bash",
    "tool_input": {
        "command": "echo 'Testing Discord hooks with proper User-Agent headers'",
        "description": "Test command",
    },
    "execution_time": 0.123,
}

# Set environment variable for event type
env = os.environ.copy()
env["CLAUDE_HOOK_EVENT"] = "PreToolUse"

print("Testing updated discord_event_logger.py...")
print(f"Event type: {env['CLAUDE_HOOK_EVENT']}")
print(f"Tool: {test_event['tool_name']}")

# Run the logger script
try:
    process = subprocess.Popen(
        ["python3", "discord_event_logger.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )

    # Send test event to stdin
    stdout, stderr = process.communicate(input=json.dumps(test_event).encode())

    print(f"\nReturn code: {process.returncode}")

    if stdout:
        print(f"Stdout: {stdout.decode()}")

    if stderr:
        print(f"Stderr: {stderr.decode()}")

    if process.returncode == 0:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed")

except Exception as e:
    print(f"\n❌ Error running test: {e}")
    sys.exit(1)
