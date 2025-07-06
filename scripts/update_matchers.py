#!/usr/bin/env python3
"""
Update settings.json matchers from '*' to empty string
"""

import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"

# Read settings
with open(settings_file, "r") as f:
    settings = json.load(f)

# Update matchers
modified = False
if "hooks" in settings:
    for event_type, event_hooks in settings["hooks"].items():
        for hook_config in event_hooks:
            if "matcher" in hook_config and hook_config["matcher"] == "*":
                hook_config["matcher"] = ""
                modified = True
                print(f"Updated matcher in {event_type} from '*' to ''")

# Write back if modified
if modified:
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)
    print(f"Updated {settings_file}")
else:
    print("No changes needed")
