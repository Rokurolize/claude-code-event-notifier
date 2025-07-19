#!/usr/bin/env python3
"""Clean up duplicate hooks in settings.json.

Removes old architecture hooks and keeps only simple architecture.
"""

import json
import sys
from pathlib import Path
from typing import Any


def should_keep_hook(hook: Any) -> bool:
    """Determine if a hook should be kept."""
    if not isinstance(hook, dict) or "hooks" not in hook:
        return False
    
    for h in hook["hooks"]:
        if "command" in h:
            cmd = h["command"]
            # Keep simple architecture
            if "src/simple/main.py" in cmd:
                return True
            # Keep CLAUDE.md reminder
            if "claude_md_reminder.py" in cmd:
                return True
            # Keep bash validator (different tool)
            if "bash_command_validator" in cmd:
                return True
            # Remove old architecture
            if "CLAUDE_HOOK_EVENT" in cmd:
                return False
            if "src/main.py" in cmd and "simple" not in cmd:
                return False
    
    return False


def clean_hooks(settings: dict) -> int:
    """Clean duplicate hooks from settings."""
    if "hooks" not in settings:
        return 0
    
    total_removed = 0
    
    for event_type in settings["hooks"]:
        original_count = len(settings["hooks"][event_type])
        
        # Filter hooks
        settings["hooks"][event_type] = [
            hook for hook in settings["hooks"][event_type]
            if should_keep_hook(hook)
        ]
        
        removed = original_count - len(settings["hooks"][event_type])
        if removed > 0:
            print(f"🧹 Removed {removed} duplicate hook(s) from {event_type}")
            total_removed += removed
    
    return total_removed


def main() -> int:
    """Main entry point."""
    settings_file = Path.home() / ".claude" / "settings.json"
    
    print("🔍 Checking for duplicate hooks...")
    
    try:
        # Load settings
        with open(settings_file, "r") as f:
            settings = json.load(f)
    except FileNotFoundError:
        print(f"❌ Settings file not found: {settings_file}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in settings file: {e}")
        return 1
    except IOError as e:
        print(f"❌ Error reading settings file: {e}")
        return 1
    
    # Clean duplicates
    removed = clean_hooks(settings)
    
    if removed == 0:
        print("✅ No duplicates found!")
        return 0
    
    try:
        # Backup original
        backup_file = settings_file.with_suffix(".json.backup")
        with open(backup_file, "w") as f:
            json.dump(json.loads(settings_file.read_text()), f, indent=2)
        print(f"💾 Backed up original to {backup_file}")
        
        # Save cleaned settings
        with open(settings_file, "w") as f:
            json.dump(settings, f, indent=2)
        
        print(f"✨ Removed {removed} duplicate hook(s) total")
        print("✅ Settings cleaned successfully!")
        
    except IOError as e:
        print(f"❌ Error writing files: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ Error processing JSON: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())