#!/usr/bin/env python3
"""Configure a Stop hook to remind about CLAUDE.md updates.

This creates a hook that triggers when Claude Code session ends,
reminding to update CLAUDE.md if significant work was done.
"""

import json
import sys
from pathlib import Path
from typing import Any, TypedDict


class HookConfig(TypedDict):
    type: str
    command: str
    pattern: str


def main() -> int:
    """Configure CLAUDE.md reminder hook."""
    settings_file = Path.home() / ".claude" / "settings.json"
    
    if not settings_file.exists():
        print("❌ Settings file not found")
        return 1
    
    # Load settings
    with open(settings_file, "r") as f:
        settings = json.load(f)
    
    if "hooks" not in settings:
        settings["hooks"] = {}
    
    if "Stop" not in settings["hooks"]:
        settings["hooks"]["Stop"] = []
    
    # Create reminder hook command
    script_path = Path(__file__).parent / "src" / "simple" / "claude_md_reminder.py"
    command = f"cd {script_path.parent.parent.parent} && uv run --python 3.14 python {script_path}"
    
    # Check if already exists
    for hook in settings["hooks"]["Stop"]:
        if isinstance(hook, dict) and "hooks" in hook:
            for h in hook["hooks"]:
                if "claude_md_reminder" in h.get("command", ""):
                    print("✅ CLAUDE.md reminder hook already configured")
                    return 0
    
    # Add new hook
    hook_config: HookConfig = {
        "type": "command",
        "command": command,
        "pattern": ".*"
    }
    
    settings["hooks"]["Stop"].append({"hooks": [hook_config]})
    
    # Save settings
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)
    
    print("✅ CLAUDE.md reminder hook added to Stop event")
    print("📝 You'll be reminded to update CLAUDE.md when sessions end")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())