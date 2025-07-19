#!/usr/bin/env python3
"""Test all event types with the simple architecture."""

import json
import subprocess
import sys
from pathlib import Path

test_events = [
    {
        "name": "PreToolUse",
        "data": {
            "session_id": "test-simple-arch",
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/test.py",
                "content": "print('Hello from simple architecture!')"
            }
        }
    },
    {
        "name": "PostToolUse",
        "data": {
            "session_id": "test-simple-arch",
            "hook_event_name": "PostToolUse",
            "tool_name": "Write",
            "tool_response": {}
        }
    },
    {
        "name": "Notification",
        "data": {
            "session_id": "test-simple-arch",
            "hook_event_name": "Notification",
            "message": "🎉 Simple architecture is working!"
        }
    },
    {
        "name": "Stop",
        "data": {
            "session_id": "test-simple-arch",
            "hook_event_name": "Stop"
        }
    },
    {
        "name": "SubagentStop",
        "data": {
            "session_id": "test-simple-arch",
            "hook_event_name": "SubagentStop"
        }
    }
]

# Test each event
for event in test_events:
    print(f"\n📨 Testing {event['name']} event...")
    
    # Run main.py with event data
    process = subprocess.run(
        ["uv", "run", "--python", "3.14", "python", "src/simple/main.py"],
        input=json.dumps(event['data']),
        text=True,
        capture_output=True
    )
    
    if process.returncode == 0:
        print(f"✅ {event['name']} - Success")
    else:
        print(f"❌ {event['name']} - Failed")
        if process.stderr:
            print(f"   Error: {process.stderr}")

print("\n✨ All tests completed!")