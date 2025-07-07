#!/usr/bin/env python3
"""
Quick test for text channel thread creation
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def test_text_thread():
    """Test text channel thread creation."""
    script_path = Path(__file__).parent / "src" / "discord_notifier.py"
    
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    session_id = f"text-thread-test-{timestamp}"
    
    # Test event
    event_data = {
        "session_id": session_id,
        "hook_event_name": "Notification",
        "message": f"🧵 Testing text channel thread creation - Session: {session_id}",
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"Testing text channel thread creation...")
    print(f"Session ID: {session_id}")
    
    env = os.environ.copy()
    env["CLAUDE_HOOK_EVENT"] = "Notification"
    env["DISCORD_DEBUG"] = "1"
    
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(event_data),
            text=True,
            capture_output=True,
            env=env,
            timeout=10,
        )
        
        print(f"Return code: {proc.returncode}")
        print(f"Output: {proc.stderr}")
        
        return proc.returncode == 0
        
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = test_text_thread()
    print("\n" + "="*50)
    if success:
        print("✅ Text channel thread test completed")
    else:
        print("❌ Text channel thread test failed")