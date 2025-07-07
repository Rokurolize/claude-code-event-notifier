#!/usr/bin/env python3
"""
Configure Claude Code hooks for Discord notifications.

This script sets up the integration between Claude Code's hook system
and Discord notifications by modifying Claude Code's settings.json.

Usage: python3 configure_hooks.py [--remove]
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


def atomic_write(filepath, content):
    """Write content to file atomically using temp file + rename."""
    filepath = Path(filepath)
    # Create temp file in same directory for same filesystem
    fd, temp_path = tempfile.mkstemp(dir=filepath.parent, text=True)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic rename
        os.rename(temp_path, filepath)
    except:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Configure Claude Code hooks for Discord notifications"
    )
    parser.add_argument(
        "--remove", action="store_true", help="Remove the notifier from Claude Code"
    )
    args = parser.parse_args()

    # Paths
    claude_dir = Path.home() / ".claude"
    hooks_dir = claude_dir / "hooks"
    settings_file = claude_dir / "settings.json"

    # Source and target for the notifier script
    source_script = Path(__file__).parent / "src" / "discord_notifier.py"
    target_script = hooks_dir / "discord_notifier.py"

    if args.remove:
        print("Removing Claude Code Discord Notifier...")

        # Remove script
        if target_script.exists():
            target_script.unlink()
            print(f"✓ Removed {target_script}")

        # Remove from settings.json
        if settings_file.exists():
            with open(settings_file) as f:
                settings = json.load(f)

            # Remove discord notifier hooks
            if "hooks" in settings:
                for event_type in settings["hooks"]:
                    settings["hooks"][event_type] = [
                        hook
                        for hook in settings["hooks"][event_type]
                        if "discord_notifier.py"
                        not in hook.get("hooks", [{}])[0].get("command", "")
                    ]

            atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")

            print("✓ Removed hooks from settings.json")

        print("\nRemoval complete!")
        return 0

    # Install mode
    print("Installing Claude Code Discord Notifier...")

    # Check source exists
    if not source_script.exists():
        print(f"Error: Source script not found at {source_script}")
        return 1

    # Create directories
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # Copy script
    shutil.copy2(source_script, target_script)
    target_script.chmod(0o755)  # Make executable
    print(f"✓ Copied notifier to {target_script}")

    # Update settings.json
    if settings_file.exists():
        with open(settings_file) as f:
            settings = json.load(f)
    else:
        settings = {}

    if "hooks" not in settings:
        settings["hooks"] = {}

    # Define hooks for each event type
    events = ["PreToolUse", "PostToolUse", "Notification", "Stop", "SubagentStop"]

    for event in events:
        if event not in settings["hooks"]:
            settings["hooks"][event] = []

        # Remove any existing discord notifier hooks
        settings["hooks"][event] = [
            hook
            for hook in settings["hooks"][event]
            if "discord_notifier.py"
            not in hook.get("hooks", [{}])[0].get("command", "")
        ]

        # Add new hook
        hook_config = {
            "hooks": [
                {
                    "type": "command",
                    "command": f"CLAUDE_HOOK_EVENT={event} python3 {target_script}",
                }
            ]
        }

        # Add matcher for tool events
        if event in ["PreToolUse", "PostToolUse"]:
            hook_config["matcher"] = []

        settings["hooks"][event].append(hook_config)

    # Save settings
    claude_dir.mkdir(exist_ok=True)
    atomic_write(settings_file, json.dumps(settings, indent=2) + "\n")

    print("✓ Updated settings.json")

    # Create example config if it doesn't exist
    env_example = hooks_dir / ".env.discord.example"
    if not env_example.exists():
        env_example.write_text("""# Discord Configuration
# Option 1: Webhook (recommended)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# Option 2: Bot Token
# DISCORD_TOKEN=your_bot_token_here
# DISCORD_CHANNEL_ID=your_channel_id_here

# Optional: Enable debug logging
# DISCORD_DEBUG=1

# Optional: Thread support for session organization
# DISCORD_USE_THREADS=1
# DISCORD_CHANNEL_TYPE=text          # "text" or "forum"
# DISCORD_THREAD_PREFIX=Session      # Custom thread name prefix
""")
        print(f"✓ Created example config at {env_example}")

    print("\n✅ Installation complete!")
    print("\nNext steps:")
    print(f"1. Copy {env_example} to {hooks_dir / '.env.discord'}")
    print("2. Edit .env.discord with your Discord credentials")
    print("3. Restart Claude Code")

    return 0


if __name__ == "__main__":
    sys.exit(main())
