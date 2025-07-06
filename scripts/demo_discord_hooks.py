#!/usr/bin/env python3
"""
Demo Discord Hooks Setup

This script demonstrates the Discord hooks configuration by creating
a sample hooks.json file in the current directory (not modifying
the actual Claude configuration).

Usage: python3 demo_discord_hooks.py
"""

import json
from pathlib import Path


def create_demo_hooks_config():
    """Create a demo hooks configuration with Discord notifications."""
    script_path = Path(__file__).parent.absolute() / "discord_event_logger.py"

    # Demo configuration
    hooks_config = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"CLAUDE_HOOK_EVENT=PreToolUse python3 {script_path}",
                        }
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"CLAUDE_HOOK_EVENT=PostToolUse python3 {script_path}",
                        }
                    ],
                }
            ],
            "Notification": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"CLAUDE_HOOK_EVENT=Notification python3 {script_path}",
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"CLAUDE_HOOK_EVENT=Stop python3 {script_path}",
                        }
                    ]
                }
            ],
            "SubagentStop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": f"CLAUDE_HOOK_EVENT=SubagentStop python3 {script_path}",
                        }
                    ]
                }
            ],
        }
    }

    return hooks_config


def main():
    """Demo the Discord hooks configuration."""
    print("Discord Hooks Configuration Demo")
    print("=" * 35)

    # Create demo configuration
    config = create_demo_hooks_config()

    # Save to local file for demonstration
    demo_file = "demo_hooks.json"
    with open(demo_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Demo configuration created: {demo_file}")
    print()
    print("This configuration would enable Discord notifications for:")
    print("  🔧 PreToolUse: Before tool execution")
    print("  ✅ PostToolUse: After tool completion")
    print("  📢 Notification: System notifications")
    print("  🏁 Stop: Session end")
    print("  🤖 SubagentStop: Subagent completion")
    print()
    print(
        f"Script path: {Path(__file__).parent.absolute() / 'discord_event_logger.py'}"
    )
    print()
    print("To apply this configuration to Claude Code:")
    print("1. Copy demo_hooks.json to ~/.claude/hooks.json")
    print("2. Or use: python3 setup_discord_hooks.py")
    print()
    print("Configuration preview:")
    print("-" * 20)

    # Show a sample configuration
    sample_hook = config["hooks"]["PreToolUse"][0]
    print(json.dumps(sample_hook, indent=2))


if __name__ == "__main__":
    main()
