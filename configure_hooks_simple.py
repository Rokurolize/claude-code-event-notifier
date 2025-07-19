#!/usr/bin/env python3
"""Configure Claude Code hooks for Discord notifications (Simple Architecture).

This script sets up the integration between Claude Code's hook system
and Discord notifications using the simple architecture.

Usage: uv run --python 3.14 python configure_hooks_simple.py [--remove]
"""

import sys

# Check Python version before any other imports
if sys.version_info < (3, 14):
    print(f"""
ERROR: This project requires Python 3.14 or higher.
Current Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}

Please run with Python 3.14+:
  uv run --python 3.14 python configure_hooks_simple.py
""", file=sys.stderr)
    sys.exit(1)

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict, Literal, Optional, Any

# Simple type definitions
HookEventType = Literal["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]

class HookConfig(TypedDict):
    """Simple hook configuration."""
    type: Literal["command"]
    command: str
    pattern: str

class CommandHook(TypedDict):
    """Command hook structure."""
    hooks: list[HookConfig]


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Configure Claude Code hooks for Discord notifications (Simple Architecture)"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove Discord notifier hooks instead of adding them"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Test Discord integration"
    )
    args = parser.parse_args()

    # Get paths
    settings_dir = Path.home() / ".claude"
    settings_file = settings_dir / "settings.json"
    
    # Get project root
    project_root = Path(__file__).parent
    source_script = project_root / "src" / "simple" / "main.py"
    
    print("🚀 Claude Code Discord Notifier Setup (Simple Architecture)")
    print(f"📁 Settings: {settings_file}")
    print(f"📝 Script: {source_script}")
    
    # Check if source script exists
    if not source_script.exists():
        print(f"❌ Script not found: {source_script}")
        return 1
    
    # Create settings directory if needed
    settings_dir.mkdir(exist_ok=True, parents=True)
    
    # Load or create settings
    if settings_file.exists():
        print("📖 Loading existing settings...")
        with open(settings_file, "r") as f:
            settings = json.load(f)
    else:
        print("📝 Creating new settings file...")
        settings = {"hooks": {}}
    
    # Ensure hooks section exists
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    # Process each event type
    events: list[HookEventType] = ["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]
    
    for event in events:
        # Ensure event array exists
        if event not in settings["hooks"]:
            settings["hooks"][event] = []
        
        # Remove existing Discord notifier hooks
        original_count = len(settings["hooks"][event])
        settings["hooks"][event] = [
            h for h in settings["hooks"][event]
            if not is_discord_notifier_hook(h)
        ]
        removed_count = original_count - len(settings["hooks"][event])
        
        if removed_count > 0:
            print(f"🧹 Removed {removed_count} existing Discord notifier hook(s) for {event}")
        
        if not args.remove:
            # Add new hook (WITHOUT CLAUDE_HOOK_EVENT)
            python_cmd_list = get_python_command(source_script.absolute())
            # Convert list back to string for settings.json
            command = " ".join(python_cmd_list)
            
            hook_config: HookConfig = {
                "type": "command",
                "command": command,
                "pattern": ".*"
            }
            
            command_hook: CommandHook = {"hooks": [hook_config]}
            settings["hooks"][event].append(command_hook)
            print(f"✅ Added Discord notifier hook for {event}")
    
    # Save settings
    print("\n💾 Saving settings...")
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)
    
    print("✨ Configuration complete!")
    
    if args.validate:
        print("\n🧪 Testing Discord integration...")
        test_discord_integration(source_script)
    
    return 0


def get_python_command(script_path: Path) -> list[str]:
    """Get the Python command for executing the script."""
    # Always use uv run with Python 3.14
    # Return as list for safe subprocess execution
    return [
        "uv", "run", "--python", "3.14", "--no-project",
        "python", str(script_path)
    ]


def is_discord_notifier_hook(hook: Any) -> bool:
    """Check if a hook is a Discord notifier hook."""
    if not isinstance(hook, dict):
        return False
    
    if "hooks" in hook and isinstance(hook["hooks"], list):
        for h in hook["hooks"]:
            if isinstance(h, dict) and "command" in h:
                cmd = h["command"]
                if "discord_notifier.py" in cmd or "discord-code-event-notifier" in cmd or "/simple/main.py" in cmd:
                    return True
    
    return False


def test_discord_integration(script_path: Path) -> None:
    """Test Discord integration by sending a test notification."""
    test_event = {
        "session_id": "test-simple-arch",
        "hook_event_name": "Notification",
        "message": "🎉 Simple architecture Discord notifier is configured!"
    }
    
    python_cmd = get_python_command(script_path)
    
    print(f"📨 Sending test notification...")
    
    try:
        result = subprocess.run(
            python_cmd,
            input=json.dumps(test_event),
            text=True,
            capture_output=True,
            cwd=script_path.parent.parent.parent  # Run from project root
        )
        
        if result.returncode == 0:
            print("✅ Test notification sent successfully!")
        else:
            print("❌ Test failed")
            if result.stderr:
                print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    sys.exit(main())