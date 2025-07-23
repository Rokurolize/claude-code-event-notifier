#!/usr/bin/env python3
"""Setup Claude Code hooks for Discord notifications (Simple Architecture).

This script configures Claude Code hooks to use the simple architecture
for Discord notifications. It follows the new hook format requirements.

Usage: 
  uv run python setup_simple.py           # Install hooks
  uv run python setup_simple.py --remove  # Remove hooks
  uv run python setup_simple.py --test    # Test configuration
"""

import sys

# Check Python version before any other imports
if sys.version_info < (3, 13):
    print(f"""
ERROR: This project requires Python 3.13 or higher.
Current Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}

Please run with Python 3.13+:
  uv run --python 3.13 python setup_simple.py
""", file=sys.stderr)
    sys.exit(1)

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


class SimpleHookSetup:
    """Setup manager for simple architecture hooks."""
    
    def __init__(self):
        self.settings_dir = Path.home() / ".claude"
        self.settings_file = self.settings_dir / "settings.json"
        self.project_root = Path(__file__).parent
        self.script_path = self.project_root / "src" / "simple" / "main.py"
        
        # Events to configure
        self.events = [
            "PreToolUse", "PostToolUse", "Notification", 
            "Stop", "SubagentStop", "UserPromptSubmit", "PreCompact"
        ]
        
    def run(self, remove: bool = False, test: bool = False) -> int:
        """Run the setup process."""
        print("🚀 Claude Code Discord Notifier Setup")
        print("📁 Architecture: Simple (Zero Dependencies)")
        print(f"📂 Settings: {self.settings_file}")
        print(f"📄 Script: {self.script_path}")
        print("")
        
        # Verify script exists
        if not self.script_path.exists():
            print(f"❌ Error: Script not found at {self.script_path}")
            return 1
            
        # Load or create settings
        settings = self._load_settings()
        
        if remove:
            self._remove_hooks(settings)
        else:
            self._add_hooks(settings)
            
        # Save settings
        self._save_settings(settings)
        
        if test and not remove:
            self._test_integration()
            
        return 0
        
    def _load_settings(self) -> dict[str, Any]:
        """Load existing settings or create new ones."""
        self.settings_dir.mkdir(exist_ok=True, parents=True)
        
        if self.settings_file.exists():
            print("📖 Loading existing settings...")
            with open(self.settings_file) as f:
                return json.load(f)
        else:
            print("📝 Creating new settings file...")
            return {}
            
    def _save_settings(self, settings: dict[str, Any]) -> None:
        """Save settings to file."""
        print("\n💾 Saving settings...")
        with open(self.settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        print("✅ Settings saved")
        
    def _remove_hooks(self, settings: dict[str, Any]) -> None:
        """Remove Discord notifier hooks."""
        print("\n🧹 Removing Discord notifier hooks...")
        
        if "hooks" not in settings:
            print("⚠️  No hooks found in settings")
            return
            
        hooks = settings["hooks"]
        total_removed = 0
        
        for event in self.events:
            if event not in hooks:
                continue
                
            original_count = len(hooks[event])
            hooks[event] = [
                hook for hook in hooks[event]
                if not self._is_notifier_hook(hook)
            ]
            
            removed = original_count - len(hooks[event])
            if removed > 0:
                print(f"  ✅ Removed {removed} hook(s) from {event}")
                total_removed += removed
                
        if total_removed == 0:
            print("  ℹ️  No Discord notifier hooks found to remove")
        else:
            print(f"\n✅ Removed {total_removed} hook(s) total")
            
    def _add_hooks(self, settings: dict[str, Any]) -> None:
        """Add Discord notifier hooks with new format."""
        print("\n📌 Adding Discord notifier hooks...")
        
        # Ensure hooks section exists
        if "hooks" not in settings:
            settings["hooks"] = {}
        hooks = settings["hooks"]
        
        # Build command
        command = f"uv run --python 3.13 --no-project python {self.script_path.absolute()}"
        
        for event in self.events:
            # Initialize event list if not exists
            if event not in hooks:
                hooks[event] = []
                
            # Remove existing notifier hooks first
            hooks[event] = [
                hook for hook in hooks[event]
                if not self._is_notifier_hook(hook)
            ]
            
            # Add new hook with correct format
            hook_entry = {
                "hooks": [
                    {
                        "type": "command",
                        "command": command
                    }
                ]
            }
            
            # Only PreToolUse and PostToolUse use matcher field
            if event in ["PreToolUse", "PostToolUse"]:
                hook_entry["matcher"] = ""  # Empty matcher matches all tools
                
            hooks[event].append(hook_entry)
            print(f"  ✅ Added hook for {event}")
            
        print(f"\n✅ Added hooks for {len(self.events)} events")
        
    def _is_notifier_hook(self, hook: Any) -> bool:
        """Check if a hook is a Discord notifier hook."""
        if not isinstance(hook, dict):
            return False
            
        # Check for hooks array
        if "hooks" in hook and isinstance(hook["hooks"], list):
            for h in hook["hooks"]:
                if isinstance(h, dict) and "command" in h:
                    cmd = h["command"]
                    # Check for various patterns that indicate our notifier
                    patterns = [
                        "simple/main.py",
                        "discord-code-event-notifier",
                        "discord_notifier.py",
                        "src/main.py"
                    ]
                    if any(pattern in cmd for pattern in patterns):
                        return True
                        
        # Legacy format check
        if "type" in hook and hook.get("type") == "command":
            cmd = hook.get("command", "")
            if "simple/main.py" in cmd or "discord" in cmd:
                return True
                
        return False
        
    def _test_integration(self) -> None:
        """Test the Discord integration."""
        print("\n🧪 Testing Discord integration...")
        
        test_event = {
            "hook_event_name": "Notification",
            "session_id": "test-session",
            "message": "✅ Discord notifier is working! (Simple Architecture)"
        }
        
        command = [
            "uv", "run", "--python", "3.13", "--no-project",
            "python", str(self.script_path.absolute())
        ]
        
        try:
            result = subprocess.run(
                command,
                input=json.dumps(test_event),
                text=True,
                capture_output=True,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                print("✅ Test notification sent successfully!")
                print("📬 Check your Discord channel for the test message")
            else:
                print("❌ Test failed")
                if result.stderr:
                    print(f"Error output:\n{result.stderr}")
                    
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup Claude Code Discord notifications (Simple Architecture)"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove Discord notifier hooks"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test Discord integration after setup"
    )
    
    args = parser.parse_args()
    
    setup = SimpleHookSetup()
    return setup.run(remove=args.remove, test=args.test)


if __name__ == "__main__":
    sys.exit(main())