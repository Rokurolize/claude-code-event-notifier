#!/usr/bin/env python3
"""Update hooks.json to use webhook URL directly"""

import json
from pathlib import Path

webhook_url = "https://discord.com/api/webhooks/1391303915022188544/2wVrqthPSKQmPceQ3rP-y-1rsbGX-hPFNml_H91ItYDKrHlUzTOWbkBOu7oMlCFDmK5z"
hooks_file = Path.home() / ".claude" / "hooks.json"

# Load existing hooks
with open(hooks_file, "r") as f:
    hooks_config = json.load(f)

# Update Discord hook commands to include webhook URL
script_path = "/home/ubuntu/human-in-the-loop/discord_event_logger.py"

for event_type in ["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]:
    if event_type in hooks_config["hooks"]:
        for config in hooks_config["hooks"][event_type]:
            for hook in config.get("hooks", []):
                if "discord_event_logger.py" in hook.get("command", ""):
                    # Update command to include webhook URL
                    hook["command"] = (
                        f'CLAUDE_HOOK_EVENT={event_type} DISCORD_WEBHOOK_URL="{webhook_url}" python3 {script_path}'
                    )

# Save updated configuration
with open(hooks_file, "w") as f:
    json.dump(hooks_config, f, indent=2)

print("✅ Updated hooks.json with webhook URL")
print(f"Webhook: {webhook_url[:50]}...")

# Show sample updated command
print("\nSample updated command:")
print(hooks_config["hooks"]["PreToolUse"][-1]["hooks"][0]["command"])
